"""
scanner.py — Core vulnerability scanning logic
Sources: OSV.dev (CVE) · GitHub Advisory DB (CVE fallback) ·
         Sonatype OSS Index (OSS) · endoflife.date (EOL) ·
         Maven Central (latest version / outdated detection)
"""
from __future__ import annotations

import re
import io
import base64
import asyncio
import logging
import aiohttp
from datetime import datetime
from lxml import etree

logger = logging.getLogger("scanner")

MAVEN_NS = "http://maven.apache.org/POM/4.0.0"

def ns(tag):
    return f"{{{MAVEN_NS}}}{tag}"

# Semaphore: max concurrent outbound HTTP requests to any single API
_OSV_SEM     = None   # initialised inside run_full_scan (needs running event loop)
_MAVEN_SEM   = None
_GENERAL_SEM = None

def _get_sem(attr: str, limit: int) -> asyncio.Semaphore:
    """Lazily create module-level semaphores inside a running event loop."""
    import sys
    this = sys.modules[__name__]
    if getattr(this, attr) is None:
        setattr(this, attr, asyncio.Semaphore(limit))
    return getattr(this, attr)

EOL_MAP = {
    "org.springframework.boot:spring-boot":                 "spring-boot",
    "org.springframework.boot:spring-boot-starter":         "spring-boot",
    "org.springframework.boot:spring-boot-starter-web":     "spring-boot",
    "org.springframework:spring-core":                      "spring-framework",
    "org.springframework:spring-context":                   "spring-framework",
    "org.springframework:spring-webmvc":                    "spring-framework",
    "org.apache.tomcat.embed:tomcat-embed-core":            "tomcat",
    "org.apache.tomcat:tomcat":                             "tomcat",
    "org.hibernate:hibernate-core":                         "hibernate",
    "io.quarkus:quarkus-core":                              "quarkus",
    "org.elasticsearch.client:elasticsearch":               "elasticsearch",
    "org.apache.struts:struts2-core":                       "apache-struts",
}

# ── Retry helper ──────────────────────────────────────────────────────────────

async def _http_post_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    sem: asyncio.Semaphore,
    *,
    json_body: dict = None,
    headers: dict = None,
    retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 25,
) -> tuple[int, any]:
    """
    POST with semaphore + exponential back-off retry.
    Returns (status_code, parsed_json_or_None).
    """
    last_exc = None
    for attempt in range(retries):
        try:
            async with sem:
                async with session.post(
                    url,
                    json=json_body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as r:
                    status = r.status
                    if status == 200:
                        data = await r.json(content_type=None)
                        return status, data
                    # 429 = rate-limited; 5xx = server error → retry
                    if status in (429, 500, 502, 503, 504):
                        wait = base_delay * (2 ** attempt)
                        logger.debug(f"HTTP {status} from {url}, retrying in {wait:.1f}s")
                        await asyncio.sleep(wait)
                        continue
                    # 4xx other than 429 = permanent client error
                    body = await r.text()
                    logger.debug(f"HTTP {status} from {url}: {body[:120]}")
                    return status, None
        except (aiohttp.ServerDisconnectedError,
                aiohttp.ClientConnectionError,
                asyncio.TimeoutError) as e:
            last_exc = e
            wait = base_delay * (2 ** attempt)
            logger.debug(f"Connection error ({e.__class__.__name__}) for {url}, "
                         f"retry {attempt+1}/{retries} in {wait:.1f}s")
            await asyncio.sleep(wait)
        except Exception as e:
            logger.warning(f"Unexpected error POSTing {url}: {e}")
            return 0, None
    logger.warning(f"All {retries} retries failed for {url}: {last_exc}")
    return 0, None


async def _http_get_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    sem: asyncio.Semaphore,
    *,
    headers: dict = None,
    retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 20,
) -> tuple[int, any]:
    """GET with semaphore + exponential back-off retry. Returns (status, json_or_None)."""
    last_exc = None
    for attempt in range(retries):
        try:
            async with sem:
                async with session.get(
                    url,
                    headers=headers or {},
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as r:
                    status = r.status
                    if status == 200:
                        data = await r.json(content_type=None)
                        return status, data
                    if status in (429, 500, 502, 503, 504):
                        wait = base_delay * (2 ** attempt)
                        await asyncio.sleep(wait)
                        continue
                    return status, None
        except (aiohttp.ServerDisconnectedError,
                aiohttp.ClientConnectionError,
                asyncio.TimeoutError) as e:
            last_exc = e
            wait = base_delay * (2 ** attempt)
            await asyncio.sleep(wait)
        except Exception as e:
            logger.warning(f"Unexpected GET error {url}: {e}")
            return 0, None
    logger.warning(f"All {retries} retries failed for GET {url}: {last_exc}")
    return 0, None


# ── CVSS helpers ──────────────────────────────────────────────────────────────

def parse_cvss_score(score_value) -> float | None:
    """
    Handle both numeric "9.8" and CVSS vector "CVSS:3.1/AV:N/..."
    Vectors don't embed the base score, so return None for them.
    """
    if score_value is None:
        return None
    s = str(score_value).strip()
    try:
        return float(s)
    except ValueError:
        pass
    # CVSS vector — no score is embedded
    if s.upper().startswith("CVSS:"):
        return None
    # Last resort: standalone decimal in 0–10 range
    m = re.search(r'\b(\d+\.\d+)\b', s)
    if m:
        val = float(m.group(1))
        if 0.0 <= val <= 10.0:
            return val
    return None


def cvss_to_severity(score) -> str:
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if score >= 9.0: return "CRITICAL"
    if score >= 7.0: return "HIGH"
    if score >= 4.0: return "MEDIUM"
    if score >= 0.1: return "LOW"
    return "NONE"


# ── Maven-aware version comparison ───────────────────────────────────────────

def _version_tuple(v: str) -> tuple:
    """
    Convert Maven version string to comparable tuple.
    Handles: 2.14.1, 4.1.42.Final, 29.0-jre, 1.0b2, etc.
    """
    qualifiers_high = {"final", "ga", "release", "sp"}
    qualifiers_low  = {"alpha", "beta", "rc", "cr", "snapshot", "m", "milestone"}
    s = re.sub(r'[\.\-]', ' ', v.lower()).strip()
    parts = s.split()
    result = []
    for p in parts:
        if p.isdigit():
            result.append((1, int(p), ""))
        elif re.match(r'^\d+', p):
            num = re.match(r'^(\d+)(.*)', p)
            n, q = int(num.group(1)), num.group(2)
            result.append((0 if q in qualifiers_low else 1, n, q))
        elif p in qualifiers_high:
            result.append((1, 0, p))
        elif p in qualifiers_low:
            result.append((0, 0, p))
        else:
            result.append((1, 0, p))
    return tuple(result)


def is_newer(latest: str, current: str) -> bool:
    try:
        return _version_tuple(latest) > _version_tuple(current)
    except Exception:
        return latest.strip() != current.strip()


# ── POM Parsing ───────────────────────────────────────────────────────────────

def parse_pom(content: bytes) -> dict:
    root = etree.fromstring(content)

    properties = {}
    props_el = root.find(ns("properties"))
    if props_el is not None:
        for child in props_el:
            if not isinstance(child.tag, str):  # skip comments / PIs
                continue
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            properties[tag] = (child.text or "").strip()

    parent_el = root.find(ns("parent"))
    parent_version = ""
    if parent_el is not None:
        parent_version = (parent_el.findtext(ns("version")) or "").strip()
        properties.setdefault("project.parent.version", parent_version)

    def resolve(value):
        if not value:
            return value
        for m in re.findall(r'\$\{([^}]+)\}', value):
            value = value.replace(f"${{{m}}}", properties.get(m, f"${{{m}}}"))
        return value

    deps = []
    seen = set()
    
    if parent_el is not None:
        parent_gid = (parent_el.findtext(ns("groupId")) or "").strip()
        parent_aid = (parent_el.findtext(ns("artifactId")) or "").strip()
        if parent_gid and parent_aid:
            deps.append({
                "groupId": parent_gid,
                "artifactId": parent_aid,
                "version": parent_version or None,
                "scope": "parent",
                "optional": False,
                "source": "direct",
            })

    def collect(section_el):
        if section_el is None:
            return
        for dep in section_el.findall(ns("dependency")):
            gid   = resolve((dep.findtext(ns("groupId"))    or "").strip())
            aid   = resolve((dep.findtext(ns("artifactId")) or "").strip())
            ver   = resolve((dep.findtext(ns("version"))    or "").strip())
            scope = (dep.findtext(ns("scope")) or "compile").strip()
            if gid and aid and not gid.startswith("${"):
                key = f"{gid}:{aid}"
                if key not in seen:
                    seen.add(key)
                    deps.append({
                        "groupId": gid, "artifactId": aid,
                        "version": ver or None, "scope": scope,
                        "optional": False, "source": "direct",
                    })

    collect(root.find(ns("dependencies")))
    dm = root.find(ns("dependencyManagement"))
    if dm is not None:
        collect(dm.find(ns("dependencies")))

    group_id    = resolve((root.findtext(ns("groupId"))    or "").strip())
    artifact_id = resolve((root.findtext(ns("artifactId")) or "").strip())
    version     = resolve((root.findtext(ns("version"))    or parent_version).strip())

    return {
        "groupId": group_id, "artifactId": artifact_id,
        "version": version, "properties": properties,
        "dependencies": deps,
    }


# ── Maven Central helpers ─────────────────────────────────────────────────────

async def fetch_latest_version(
    session: aiohttp.ClientSession, gid: str, aid: str
) -> str | None:
    sem = _get_sem("_MAVEN_SEM", 5)
    url = (f"https://search.maven.org/solrsearch/select"
           f"?q=g:{gid}+AND+a:{aid}&core=gav&rows=1&wt=json")
    status, data = await _http_get_with_retry(session, url, sem, timeout=12)
    if data:
        docs = data.get("response", {}).get("docs", [])
        return docs[0].get("v") if docs else None
    return None


async def fetch_transitive(session: aiohttp.ClientSession, dep: dict) -> list:
    sem = _get_sem("_MAVEN_SEM", 5)
    gid, aid, ver = dep["groupId"], dep["artifactId"], dep.get("version")
    if not ver or "$" in ver:
        return []
    gid_path = gid.replace(".", "/")
    url = f"https://repo1.maven.org/maven2/{gid_path}/{aid}/{ver}/{aid}-{ver}.pom"
    status, data = await _http_get_with_retry(session, url, sem, timeout=12)
    if status != 200 or data is None:
        # fetch_transitive gets raw bytes not JSON — use direct request
        try:
            async with sem:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=12)
                ) as r:
                    if r.status != 200:
                        return []
                    content = await r.read()
        except Exception:
            return []
    else:
        return []

    try:
        root = etree.fromstring(content)
    except Exception:
        return []

    results = []
    for d in root.findall(f".//{ns('dependency')}"):
        scope = (d.findtext(ns("scope")) or "compile").strip()
        if scope in ("test", "provided", "system", "import"):
            continue
        tgid = (d.findtext(ns("groupId"))    or "").strip()
        taid = (d.findtext(ns("artifactId")) or "").strip()
        tver = (d.findtext(ns("version"))    or "").strip()
        if tgid and taid and tver and "$" not in tver and "$" not in tgid:
            results.append({
                "groupId": tgid, "artifactId": taid,
                "version": tver, "scope": scope,
                "optional": False, "source": "transitive",
                "via": f"{gid}:{aid}:{ver}",
            })
    return results


# ── OSV.dev CVE check ─────────────────────────────────────────────────────────

async def check_osv(session: aiohttp.ClientSession, dep: dict) -> list:
    """
    Query OSV.dev for CVEs with semaphore + retry.
    Falls back to package-only query if version query returns nothing.
    """
    ver = dep.get("version")
    if not ver or "$" in ver or ver == "unknown":
        return []

    sem = _get_sem("_OSV_SEM", 4)   # max 4 concurrent OSV requests
    gid, aid = dep["groupId"], dep["artifactId"]
    package_name = f"{gid}:{aid}"

    # ── Primary: version-specific query ──────────────────────────────────────
    status, data = await _http_post_with_retry(
        session,
        "https://api.osv.dev/v1/query",
        sem,
        json_body={"version": ver,
                   "package": {"name": package_name, "ecosystem": "Maven"}},
        base_delay=2.0,
        retries=3,
    )

    raw_vulns = []
    if data is not None:
        raw_vulns = data.get("vulns", [])

    # ── Fallback: package-only query → filter by version range ───────────────
    if not raw_vulns and status in (0, 200):
        status2, data2 = await _http_post_with_retry(
            session,
            "https://api.osv.dev/v1/query",
            sem,
            json_body={"package": {"name": package_name, "ecosystem": "Maven"}},
            base_delay=2.0,
            retries=2,
        )
        if data2:
            all_vulns = data2.get("vulns", [])
            raw_vulns = _filter_osv_by_version(all_vulns, ver)

    return _parse_osv_vulns(raw_vulns)


def _filter_osv_by_version(vulns: list, target_ver: str) -> list:
    """Keep only OSV advisories whose affected ranges include target_ver."""
    matching = []
    for v in vulns:
        for affected in v.get("affected", []):
            versions = affected.get("versions", [])
            if target_ver in versions:
                matching.append(v)
                break
            for rng in affected.get("ranges", []):
                events = rng.get("events", [])
                introduced, fixed = None, None
                for evt in events:
                    if "introduced" in evt:
                        introduced = evt["introduced"]
                    if "fixed" in evt:
                        fixed = evt["fixed"]
                if introduced is not None:
                    intro_ok = (introduced in ("0", target_ver)
                                or is_newer(target_ver, introduced))
                    if intro_ok:
                        if fixed is None or is_newer(fixed, target_ver):
                            matching.append(v)
                            break
    return matching


def _parse_osv_vulns(raw_vulns: list) -> list:
    results = []
    seen_ids: set = set()
    for v in raw_vulns:
        if not isinstance(v, dict):
            continue
        vid = v.get("id", "")
        if vid in seen_ids:
            continue
        seen_ids.add(vid)

        cve_ids = [a["id"] for a in v.get("aliases", [])
                   if isinstance(a, dict) and "CVE" in a.get("id", "")] or [vid]

        severity, cvss_score = "UNKNOWN", None
        for sev in v.get("severity", []):
            if not isinstance(sev, dict):
                continue
            parsed = parse_cvss_score(sev.get("score"))
            if parsed is not None:
                cvss_score = parsed
                severity = cvss_to_severity(cvss_score)
                break

        # Fallback severity from database_specific
        if cvss_score is None:
            db = v.get("database_specific", {}) or {}
            for key in ("cvss", "cvss_score", "severity"):
                raw = db.get(key)
                if raw:
                    parsed = parse_cvss_score(raw)
                    if parsed is not None:
                        cvss_score = parsed
                        severity = cvss_to_severity(cvss_score)
                        break
                    if isinstance(raw, str) and raw.upper() in ("CRITICAL","HIGH","MEDIUM","LOW"):
                        severity = raw.upper()
                        break

        # Best fixed version
        fixed = None
        for affected in v.get("affected", []):
            if not isinstance(affected, dict):
                continue
            for rng in affected.get("ranges", []):
                if not isinstance(rng, dict):
                    continue
                for evt in rng.get("events", []):
                    if not isinstance(evt, dict):
                        continue
                    fv = evt.get("fixed")
                    if fv and fv != "0":
                        if fixed is None or is_newer(fv, fixed):
                            fixed = fv

        results.append({
            "source":        "OSV",
            "cve_ids":       cve_ids,
            "summary":       (v.get("summary") or v.get("details") or "No summary.")[:300],
            "severity":      severity,
            "cvss_score":    cvss_score,
            "fixed_version": fixed,
            "url":           f"https://osv.dev/vulnerability/{vid}",
            "published":     v.get("published", "")[:10],
        })
    return results


# ── GitHub Advisory Database (fallback CVE source) ───────────────────────────

_GHSA_MAVEN_CACHE: dict = {}

async def check_github_advisories(session: aiohttp.ClientSession, dep: dict) -> list:
    """
    Query GitHub Advisory DB. No auth required for public advisories.
    Robust against non-list responses (rate limit pages, error objects).
    """
    ver = dep.get("version")
    if not ver or "$" in ver or ver == "unknown":
        return []

    sem = _get_sem("_GENERAL_SEM", 5)
    gid, aid = dep["groupId"], dep["artifactId"]
    cache_key = f"{gid}:{aid}:{ver}"
    if cache_key in _GHSA_MAVEN_CACHE:
        return _GHSA_MAVEN_CACHE[cache_key]

    pkg = f"{gid}:{aid}"
    url = (f"https://api.github.com/advisories"
           f"?ecosystem=maven&package={pkg}&per_page=20")
    status, raw = await _http_get_with_retry(
        session, url, sem,
        headers={"Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        timeout=15,
    )

    # Guard: response must be a list of dicts
    if not isinstance(raw, list):
        _GHSA_MAVEN_CACHE[cache_key] = []
        return []

    results = []
    for adv in raw:
        # Guard: each advisory must be a dict
        if not isinstance(adv, dict):
            continue

        # Filter: only keep advisories that affect this version
        affects_this_ver = False
        for vuln in adv.get("vulnerabilities", []):
            if not isinstance(vuln, dict):
                continue
            vuln_pkg = vuln.get("package", {}) or {}
            pkg_name = f"{vuln_pkg.get('namespace', '')}:{vuln_pkg.get('name', '')}"
            if pkg.lower() not in pkg_name.lower() and pkg_name not in (":", ""):
                continue
            vuln_range = vuln.get("vulnerable_version_range") or ""
            patched    = vuln.get("patched_versions") or ""
            # If patched version exists and our version is older, we're affected
            patch_m = re.search(r'[\d]+\.[\d]+[\d.A-Za-z\-]*', patched)
            if patch_m and is_newer(patch_m.group(0), ver):
                affects_this_ver = True
                break
            # If no patched version info, include the advisory anyway
            if not patched:
                affects_this_ver = True
                break

        if not affects_this_ver and adv.get("vulnerabilities"):
            continue

        cve_ids = [adv["cve_id"]] if adv.get("cve_id") else []
        ghsa_id = adv.get("ghsa_id", "")
        if not cve_ids:
            cve_ids = [ghsa_id] if ghsa_id else ["N/A"]

        sev_map = {"CRITICAL": 9.5, "HIGH": 7.5, "MODERATE": 5.5, "LOW": 2.0}
        sev_str = (adv.get("severity") or "UNKNOWN").upper()
        if sev_str == "MODERATE":
            sev_str = "MEDIUM"
        cvss_score = sev_map.get(sev_str)

        # Extract fixed version
        fixed = None
        for vuln in adv.get("vulnerabilities", []):
            if not isinstance(vuln, dict):
                continue
            fv_raw = vuln.get("patched_versions") or ""
            m = re.search(r'[\d]+\.[\d]+[\d.A-Za-z\-]*', fv_raw)
            if m:
                candidate = m.group(0)
                if fixed is None or is_newer(candidate, fixed):
                    fixed = candidate

        results.append({
            "source":        "GitHub",
            "cve_ids":       cve_ids,
            "summary":       (adv.get("summary") or "No summary.")[:300],
            "severity":      sev_str,
            "cvss_score":    cvss_score,
            "fixed_version": fixed,
            "url":           f"https://github.com/advisories/{ghsa_id}",
            "published":     (adv.get("published_at") or "")[:10],
        })

    _GHSA_MAVEN_CACHE[cache_key] = results
    return results


# ── Sonatype OSS Index ────────────────────────────────────────────────────────

async def check_oss_index_batch(
    session: aiohttp.ClientSession, deps: list,
    oss_user=None, oss_token=None,
) -> dict:
    purls = {}
    for dep in deps:
        ver = dep.get("version")
        if not ver or "$" in ver or ver == "unknown":
            continue
        purl = f"pkg:maven/{dep['groupId']}/{dep['artifactId']}@{ver}"
        key  = f"{dep['groupId']}:{dep['artifactId']}:{ver}"
        purls[purl] = key

    if not purls:
        return {}

    results = {}
    sem = _get_sem("_GENERAL_SEM", 5)
    auth_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if oss_user and oss_token:
        creds = base64.b64encode(f"{oss_user}:{oss_token}".encode()).decode()
        auth_headers["Authorization"] = f"Basic {creds}"
    pub_headers = {k: v for k, v in auth_headers.items() if k != "Authorization"}

    purl_list = list(purls.keys())
    for i in range(0, len(purl_list), 128):
        batch = purl_list[i: i + 128]
        try:
            if oss_user and oss_token:
                url = "https://ossindex.sonatype.org/api/v3/authorized/component-report"
                headers = auth_headers
            else:
                url = "https://ossindex.sonatype.org/api/v3/component-report"
                headers = pub_headers

            status, comps = await _http_post_with_retry(
                session, url, sem,
                json_body={"coordinates": batch},
                headers=headers,
                retries=2, base_delay=2.0,
            )

            # If auth endpoint 401'd, retry with public endpoint
            if status == 401:
                status, comps = await _http_post_with_retry(
                    session,
                    "https://ossindex.sonatype.org/api/v3/component-report",
                    sem,
                    json_body={"coordinates": batch},
                    headers=pub_headers,
                    retries=2, base_delay=2.0,
                )

            if not isinstance(comps, list):
                continue

            for comp in comps:
                if not isinstance(comp, dict):
                    continue
                coord = comp.get("coordinates", "")
                key   = purls.get(coord)
                if not key:
                    continue
                parsed = []
                for v in comp.get("vulnerabilities", []):
                    if not isinstance(v, dict):
                        continue
                    score = v.get("cvssScore", 0.0)
                    parsed.append({
                        "source":      "OSSIndex",
                        "cve_id":      v.get("cve", v.get("id", "N/A")),
                        "title":       (v.get("title") or "")[:200],
                        "description": (v.get("description") or "")[:350],
                        "cvss_score":  score,
                        "severity":    cvss_to_severity(score),
                        "reference":   v.get("reference", ""),
                    })
                results[key] = parsed
        except Exception as e:
            logger.warning(f"OSS Index batch error: {e}")
    return results


# ── endoflife.date ────────────────────────────────────────────────────────────

_eol_cache: dict = {}

async def check_eol(session: aiohttp.ClientSession, product: str, version: str):
    if not product or not version or "$" in version or version == "unknown":
        return None

    sem = _get_sem("_GENERAL_SEM", 5)
    if product not in _eol_cache:
        status, data = await _http_get_with_retry(
            session,
            f"https://endoflife.date/api/{product}.json",
            sem, timeout=10,
        )
        if not isinstance(data, list):
            return None
        _eol_cache[product] = data

    data  = _eol_cache[product]
    parts = version.split(".")
    candidates = {version,
                  ".".join(parts[:2]) if len(parts) >= 2 else parts[0],
                  parts[0]}

    for cycle_data in data:
        if not isinstance(cycle_data, dict):
            continue
        if str(cycle_data.get("cycle", "")) in candidates:
            eol_val = cycle_data.get("eol", False)
            if isinstance(eol_val, bool):
                is_eol, eol_date = eol_val, ("Yes" if eol_val else "No")
            else:
                eol_date = str(eol_val)
                try:
                    is_eol = datetime.strptime(eol_date, "%Y-%m-%d") < datetime.now()
                except Exception:
                    is_eol = False
            return {
                "product":     product,
                "cycle":       str(cycle_data.get("cycle", "")),
                "is_eol":      is_eol,
                "eol_date":    eol_date,
                "latest":      cycle_data.get("latest", "N/A"),
                "lts":         cycle_data.get("lts", False),
                "support_end": str(cycle_data.get("support", "N/A")),
            }
    return None


# ── Full scan ─────────────────────────────────────────────────────────────────

async def run_full_scan(
    pom_content: bytes,
    oss_user=None, oss_token=None,
    include_transitive: bool = True,
) -> dict:
    # Reset semaphores for each new scan (in case event loop changed)
    import sys
    this = sys.modules[__name__]
    this._OSV_SEM     = asyncio.Semaphore(4)   # max 4 concurrent OSV requests
    this._MAVEN_SEM   = asyncio.Semaphore(5)   # max 5 concurrent Maven Central requests
    this._GENERAL_SEM = asyncio.Semaphore(8)   # max 8 for GitHub/OSS Index/EOL

    parsed      = parse_pom(pom_content)
    direct_deps = parsed["dependencies"]

    # Shared TCP connector with connection limits
    connector = aiohttp.TCPConnector(limit=20, limit_per_host=6, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        all_deps = list(direct_deps)

        # 1. Collect transitive deps (concurrently, bounded by semaphore)
        if include_transitive:
            batches = await asyncio.gather(
                *[fetch_transitive(session, d) for d in direct_deps],
                return_exceptions=True,
            )
            seen = {f"{d['groupId']}:{d['artifactId']}" for d in direct_deps}
            for batch in batches:
                if isinstance(batch, list):
                    for td in batch:
                        k = f"{td['groupId']}:{td['artifactId']}"
                        if k not in seen:
                            seen.add(k)
                            all_deps.append(td)

        # 2. Batch OSS Index (one HTTP call for all deps)
        oss_results = await check_oss_index_batch(session, all_deps, oss_user, oss_token)

        # 3. Per-dep: OSV + GitHub + EOL + latest version
        async def scan_one(dep):
            gid, aid = dep["groupId"], dep["artifactId"]
            ver = dep.get("version") or "unknown"
            key = f"{gid}:{aid}:{ver}"

            # Always fetch latest version
            latest_version = None
            if ver != "unknown" and "$" not in ver:
                latest_version = await fetch_latest_version(session, gid, aid)

            # CVE: OSV first, then GitHub if OSV returns nothing
            cve_findings = await check_osv(session, dep)
            if not cve_findings:
                cve_findings = await check_github_advisories(session, dep)

            # OSS (pre-fetched in batch)
            oss_findings = oss_results.get(key, [])

            # EOL
            eol_product = EOL_MAP.get(f"{gid}:{aid}")
            eol_info = await check_eol(session, eol_product, ver) if eol_product else None

            # Outdated check
            is_outdated = bool(
                latest_version
                and ver != "unknown"
                and "$" not in ver
                and is_newer(latest_version, ver)
            )

            # Best recommended version = highest of (CVE fix, latest)
            fixed_version = None
            for f in cve_findings:
                fv = f.get("fixed_version") if isinstance(f, dict) else None
                if fv:
                    if fixed_version is None or is_newer(fv, fixed_version):
                        fixed_version = fv
            
            # Prevent hallucinated/bad advisory data: if fixed_version is strictly newer
            # than the actual latest version in Maven Central, it does not exist.
            if latest_version and fixed_version and is_newer(fixed_version, latest_version):
                fixed_version = None

            if latest_version:
                if fixed_version is None or is_newer(latest_version, fixed_version):
                    fixed_version = latest_version

            has_issues = bool(
                cve_findings
                or oss_findings
                or (eol_info and eol_info.get("is_eol"))
                or is_outdated
            )

            return {
                "groupId":        gid,
                "artifactId":     aid,
                "version":        ver,
                "scope":          dep.get("scope", "compile"),
                "source":         dep.get("source", "direct"),
                "via":            dep.get("via"),
                "cve_findings":   cve_findings,
                "oss_findings":   oss_findings,
                "eol_info":       eol_info,
                "latest_version": latest_version,
                "fixed_version":  fixed_version,
                "is_outdated":    is_outdated,
                "has_issues":     has_issues,
            }

        scan_results = await asyncio.gather(*[scan_one(d) for d in all_deps])

    return {
        "project": {
            "groupId":    parsed["groupId"],
            "artifactId": parsed["artifactId"],
            "version":    parsed["version"],
        },
        "scan_results": list(scan_results),
        "scanned_at":   datetime.now().isoformat(),
        "total":        len(scan_results),
        "issues":       sum(1 for r in scan_results if r["has_issues"]),
    }


# ── POM Fixer ─────────────────────────────────────────────────────────────────

def generate_fixed_pom(original_content: bytes, scan_results: list):
    """
    Update ALL dep versions where fixed_version is newer than current.
    Handles both direct version tags and ${property} references.
    """
    fix_map = {}
    for r in scan_results:
        if not isinstance(r, dict):
            continue
        fv  = r.get("fixed_version")
        ver = r.get("version", "unknown")
        if fv and ver != "unknown" and "$" not in ver and is_newer(fv, ver):
            fix_map[f"{r['groupId']}:{r['artifactId']}"] = fv

    parser = etree.XMLParser(remove_blank_text=False, remove_comments=False)
    tree   = etree.parse(io.BytesIO(original_content), parser)
    root   = tree.getroot()

    properties = {}
    props_el = root.find(ns("properties"))
    if props_el is not None:
        for child in props_el:
            if not isinstance(child.tag, str):  # skip comments / PIs
                continue
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            properties[tag] = (child.text or "").strip()

    updated       = []
    patched_props = set()

    def patch(section_el):
        if section_el is None:
            return
        for dep in section_el.findall(ns("dependency")):
            gid_el = dep.find(ns("groupId"))
            aid_el = dep.find(ns("artifactId"))
            ver_el = dep.find(ns("version"))
            if gid_el is None or aid_el is None or ver_el is None:
                continue
            key     = f"{(gid_el.text or '').strip()}:{(aid_el.text or '').strip()}"
            new_ver = fix_map.get(key)
            if not new_ver:
                continue
            old_ver = (ver_el.text or "").strip()
            prop_m  = re.match(r'^\$\{([^}]+)\}$', old_ver)
            if prop_m and props_el is not None:
                prop_key = prop_m.group(1)
                display_old_ver = properties.get(prop_key, old_ver)
                if prop_key not in patched_props:
                    for child in props_el:
                        if not isinstance(child.tag, str):  # skip comments / PIs
                            continue
                        ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        if ctag == prop_key:
                            child.text = new_ver
                            patched_props.add(prop_key)
                            updated.append((key, display_old_ver, new_ver, f"property ${{{prop_key}}}"))
                            break
            else:
                if old_ver != new_ver:
                    ver_el.text = new_ver
                    updated.append((key, old_ver, new_ver, "direct"))

    patch(root.find(ns("dependencies")))
    dm = root.find(ns("dependencyManagement"))
    if dm is not None:
        patch(dm.find(ns("dependencies")))

    # Also check and update parent POM
    parent_el = root.find(ns("parent"))
    if parent_el is not None:
        p_gid_el = parent_el.find(ns("groupId"))
        p_aid_el = parent_el.find(ns("artifactId"))
        p_ver_el = parent_el.find(ns("version"))
        if p_gid_el is not None and p_aid_el is not None and p_ver_el is not None:
            key = f"{(p_gid_el.text or '').strip()}:{(p_aid_el.text or '').strip()}"
            new_ver = fix_map.get(key)
            if new_ver:
                old_ver = (p_ver_el.text or "").strip()
                if old_ver != new_ver:
                    p_ver_el.text = new_ver
                    updated.append((key, old_ver, new_ver, "parent block"))

    output = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return output, updated
