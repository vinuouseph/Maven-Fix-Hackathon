"""
pom_review_gate.py
──────────────────
Shared in-memory gate for the POM vulnerability-patch review interrupt.

When vuln_scan_node computes updated dependency versions it calls
`register_review()` to get a threading.Event, dispatches a custom SSE event
carrying the old + new pom content and the review token, then blocks on
`event.wait(timeout)`.

The FastAPI endpoint `POST /api/v1/chat/compile-fix/pom-review` calls
`resolve_review(token, approved)` which unblocks the waiting thread.

This is thread-safe because:
  - vuln_scan_node runs in a thread pool (sync LangGraph node via
    run_in_executor), so `.wait()` blocks only that worker thread.
  - The FastAPI async event loop is never blocked — it just sets an event.
"""

from __future__ import annotations

import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── In-memory stores (process-scoped, survives the duration of one request) ──
_pom_review_events: dict[str, threading.Event] = {}
_pom_review_decisions: dict[str, Optional[bool]] = {}

# Maximum seconds to wait for a user decision before auto-cancelling
REVIEW_TIMEOUT_SECONDS = 600  # 10 minutes


def register_review(token: str) -> threading.Event:
    """
    Register a new review gate.  Returns a threading.Event the caller
    should block on with `.wait(REVIEW_TIMEOUT_SECONDS)`.
    """
    ev = threading.Event()
    _pom_review_events[token] = ev
    _pom_review_decisions[token] = None   # undecided
    logger.info(f"[pom_review_gate] Registered review gate for token={token[:8]}…")
    return ev


def resolve_review(token: str, approved: bool) -> bool:
    """
    Called by the HTTP endpoint to signal the waiting node.
    Returns True if the token was found, False if it had already expired.
    """
    ev = _pom_review_events.get(token)
    if ev is None:
        logger.warning(f"[pom_review_gate] Token not found or already expired: {token[:8]}…")
        return False
    _pom_review_decisions[token] = approved
    ev.set()
    logger.info(f"[pom_review_gate] Resolved token={token[:8]}… approved={approved}")
    return True


def get_decision(token: str) -> bool:
    """Return the user decision (default False = cancelled if unset)."""
    decision = _pom_review_decisions.get(token)
    return bool(decision)


def cleanup(token: str) -> None:
    """Remove entries after the node has read the decision."""
    _pom_review_events.pop(token, None)
    _pom_review_decisions.pop(token, None)
