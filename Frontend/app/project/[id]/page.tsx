'use client';
import { useParams } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import PipelineProgress, { PipelineStep } from '@/components/PipelineProgress';
import LogStream, { LogEntry } from '@/components/LogStream';
import TokenPieChart from '@/components/TokenPieChart';
import { getProject, getDownloadUrl } from '@/lib/api';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface ProjectData {
  id: number;
  project_name: string;
  project_description?: string;
  project_type: string;
  git_repo_url: string;
  status: 'running' | 'success' | 'abort' | 'escalate' | 'pending';
}

// ─── Status config ─────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  running: '#f59e0b',
  success: '#10b981',
  abort: '#ef4444',
  escalate: '#f97316',
  pending: '#64748b',
};

// ─── Component ─────────────────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const params = useParams();
  const rawId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const projectId = Number(rawId) || 0;

  const [project, setProject] = useState<ProjectData | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [projectError, setProjectError] = useState<string | null>(null);

  const [steps, setSteps] = useState<PipelineStep[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [vulnUpdates, setVulnUpdates] = useState<Array<{ dep: string; from_ver: string; to_ver: string }>>([]);
  const [vulnSummary, setVulnSummary] = useState<string>('');

  const [activeTab, setActiveTab] = useState<'pipeline' | 'logs' | 'vuln' | 'tokens'>('pipeline');
  const [tokenData, setTokenData] = useState([]);

  // ── Fetch project metadata ──────────────────────────────────────────────────

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    setLoadingProject(true);
    setProjectError(null);
    try {
      const res = await getProject(projectId);
      if (res.project_details) {
        const pd = res.project_details;
        setProject({
          id: pd.project_id,
          project_name: pd.project_name,
          project_description: pd.project_description,
          project_type: pd.project_type,
          git_repo_url: pd.git_repo_url,
          status: 'pending', // real status comes from pipeline SSE stream
        });
      } else {
        setProjectError('Project not found.');
      }
    } catch (err: unknown) {
      setProjectError(err instanceof Error ? err.message : 'Failed to load project');
    } finally {
      setLoadingProject(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  useEffect(() => {
    if (activeTab === 'tokens' && projectId) {
      import('@/lib/api').then(({ API_BASE }) => {
        fetch(`${API_BASE}/git/token-analysis/${projectId}`)
          .then((res) => res.json())
          .then((json) => setTokenData(json.data || []))
          .catch(console.error);
      });
    }
  }, [activeTab, projectId]);

  // ── Helper: upsert a pipeline step by id ───────────────────────────────────

  const upsertStep = useCallback(
    (id: string, title: string, detail: string, status: PipelineStep['status']) => {
      setSteps((prev) => {
        const idx = prev.findIndex((s) => s.id === id);
        const updated: PipelineStep = { id, title, detail, status };
        if (idx === -1) return [...prev, updated];
        const next = [...prev];
        next[idx] = updated;
        return next;
      });
    },
    []
  );

  // ── Subscribe to SSE pipeline events ───────────────────────────────────────

  useEffect(() => {
    if (!projectId) return;

    // Route SSE through the Next.js /api rewrite proxy (same as all other API calls)
    const sseBase = (process.env.NEXT_PUBLIC_API_URL) ||
      `${process.env.NEXT_PUBLIC_BASE_PATH || ''}/api`;
    const sseUrl = `${sseBase}/git/stream/${projectId}`;
    const es = new EventSource(sseUrl);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as Record<string, unknown>;
        const type = data.type as string;

        // ── Trace events → update pipeline steps ──────────────────────────
        if (type === 'trace') {
          const stepId = (data.id as string) ?? 'unknown';
          const stepTitle = (data.title as string) ?? stepId;
          const stepDetail = (data.detail as string) ?? '';
          const stepStatus = (data.status as string) ?? 'running';

          const mappedStatus: PipelineStep['status'] =
            stepStatus === 'completed' ? 'completed'
              : stepStatus === 'running' ? 'running'
                : stepStatus === 'warning' ? 'warning'
                  : stepStatus === 'error' ? 'error'
                    : 'pending';

          upsertStep(stepId, stepTitle, stepDetail, mappedStatus);

          // Log it too
          setLogs((prev) => [
            ...prev,
            {
              type: mappedStatus === 'completed' ? 'success'
                : mappedStatus === 'warning' ? 'warn'
                  : mappedStatus === 'error' ? 'error'
                    : 'trace',
              message: `[${stepId}] ${stepDetail || stepTitle}`,
              timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
            },
          ]);
        }

        // ── Delta events → stream LLM output to logs ──────────────────────
        if (type === 'delta') {
          const content = (data.content as string) ?? '';
          if (content.trim()) {
            setLogs((prev) => [
              ...prev,
              {
                type: 'delta',
                message: content,
                timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
              },
            ]);
          }
        }

        // ── Custom node events (vuln scan results, etc.) ──────────────────
        if (type === 'custom_node_event') {
          const eventName = (data.event_name as string) ?? '';
          const payload = (data.data as Record<string, unknown>) ?? {};

          if (eventName === 'project_fix_trace') {
            const vuln = payload.vuln_updates as Array<{ dep: string; from_ver: string; to_ver: string }>;
            if (vuln?.length) setVulnUpdates(vuln);
            const vs = payload.vuln_summary as string;
            if (vs) setVulnSummary(vs);
          }
        }

        // ── Terminal status ───────────────────────────────────────────────
        if (type === 'trace') {
          const stepId = (data.id as string) ?? '';
          if (['success', 'abort', 'escalate'].includes(stepId)) {
            setProject((prev) =>
              prev ? { ...prev, status: stepId as ProjectData['status'] } : prev
            );
            if (stepId === 'success') es.close();
            if (stepId === 'abort' || stepId === 'escalate') es.close();
          }
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      // SSE connection dropped — pipeline likely finished or not yet started
      es.close();
    };

    return () => es.close();
  }, [projectId, upsertStep]);

  // ── Derived ───────────────────────────────────────────────────────────────

  const isRunning = project?.status === 'running';
  const statusColor = STATUS_COLOR[project?.status ?? 'pending'] ?? '#64748b';
  const downloadUrl = project ? getDownloadUrl(project.git_repo_url) : '#';

  // ── Skeleton loader ───────────────────────────────────────────────────────

  if (loadingProject) {
    return (
      <>
        <Navbar />
        <main style={{ minHeight: '100vh', paddingTop: 88 }}>
          <div className="container" style={{ paddingTop: 32 }}>
            <div
              style={{
                height: 200,
                border: '1px solid rgba(255,255,255,0.05)',
                borderRadius: 24,
                background: 'linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%)',
                backgroundSize: '200% 100%',
                animation: 'shimmer 1.6s ease-in-out infinite',
              }}
            />
          </div>
        </main>
        <style>{`
          @keyframes shimmer { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
        `}</style>
      </>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────

  if (projectError || !project) {
    return (
      <>
        <Navbar />
        <main style={{ minHeight: '100vh', paddingTop: 88 }}>
          <div className="container" style={{ paddingTop: 32 }}>
            <div className="empty-state">
              <div className="empty-state-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 700 }}>Project not found</h3>
              <p style={{ color: '#64748b', fontSize: 14 }}>
                {projectError ?? `No project with ID ${projectId} exists.`}
              </p>
              <Link href="/dashboard" className="btn btn-ghost btn-sm" style={{ textDecoration: 'none' }}>
                ← Back to Dashboard
              </Link>
            </div>
          </div>
        </main>
      </>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────

  return (
    <>
      <Navbar />
      <main style={{ minHeight: '100vh', paddingTop: 88 }}>
        {/* Background */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: `radial-gradient(circle at 15% 30%, rgba(16,185,129,0.05) 0%, transparent 50%)`,
            pointerEvents: 'none',
            zIndex: 0,
          }}
        />

        <div
          className="container"
          style={{ position: 'relative', zIndex: 1, paddingTop: 32, paddingBottom: 80 }}
        >
          {/* Breadcrumb */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 28,
              fontSize: 13,
              color: '#475569',
            }}
          >
            <Link
              href="/dashboard"
              style={{ color: '#64748b', textDecoration: 'none' }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = '#94a3b8')}
              onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = '#64748b')}
            >
              Dashboard
            </Link>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 18l6-6-6-6" />
            </svg>
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{project.project_name}</span>
          </div>

          {/* Project header */}
          <div
            style={{
              background: 'rgba(15,23,42,0.7)',
              border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: 24,
              padding: '28px 32px',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              marginBottom: 28,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 16,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
                {/* Build tool icon */}
                <div
                  style={{
                    width: 60,
                    height: 60,
                    borderRadius: 16,
                    background:
                      project.project_type === 'maven'
                        ? 'rgba(16,185,129,0.12)'
                        : 'rgba(6,182,212,0.12)',
                    border:
                      project.project_type === 'maven'
                        ? '1px solid rgba(16,185,129,0.25)'
                        : '1px solid rgba(6,182,212,0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 26,
                  }}
                >
                  {project.project_type === 'maven' ? '🏗️' : '🐘'}
                </div>

                <div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      marginBottom: 4,
                      flexWrap: 'wrap',
                    }}
                  >
                    <h1 style={{ fontSize: 24, fontWeight: 900, letterSpacing: '-0.02em' }}>
                      {project.project_name}
                    </h1>

                    {/* Status badge */}
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '3px 10px',
                        borderRadius: 100,
                        background: `${statusColor}15`,
                        border: `1px solid ${statusColor}35`,
                        fontSize: 11,
                        fontWeight: 700,
                        color: statusColor,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}
                    >
                      <div
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          background: statusColor,
                          boxShadow: isRunning ? `0 0 8px ${statusColor}` : 'none',
                          animation: isRunning
                            ? 'pulse-glow 1.5s ease-in-out infinite'
                            : 'none',
                        }}
                      />
                      {project.status}
                    </div>
                  </div>

                  <div style={{ fontSize: 13, color: '#64748b' }}>
                    #{project.id} · {project.project_type.toUpperCase()} ·{' '}
                    <span
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 12,
                      }}
                    >
                      {project.git_repo_url.replace('https://', '')}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                {project.status === 'success' && (
                  <a
                    href={downloadUrl}
                    id="download-project-btn"
                    className="btn btn-primary btn-sm"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                    >
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Download Fixed Project
                  </a>
                )}
                <Link
                  href="/dashboard"
                  className="btn btn-ghost btn-sm"
                  style={{ textDecoration: 'none' }}
                >
                  ← Back
                </Link>
              </div>
            </div>

            {project.project_description && (
              <p style={{ fontSize: 14, color: '#64748b', marginTop: 16, lineHeight: 1.6 }}>
                {project.project_description}
              </p>
            )}
          </div>

          {/* Tab navigation */}
          <div
            style={{
              display: 'flex',
              gap: 4,
              marginBottom: 24,
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.05)',
              borderRadius: 12,
              padding: 4,
              width: 'fit-content',
            }}
          >
            {[
              { id: 'pipeline', label: 'Pipeline Progress', icon: '⚙️' },
              { id: 'logs', label: 'Live Logs', icon: '📋' },
              { id: 'vuln', label: 'Vulnerability Report', icon: '🛡️' },
              { id: 'tokens', label: 'Token Analysis', icon: '📊' },
            ].map((tab) => (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                style={{
                  padding: '8px 20px',
                  borderRadius: 8,
                  border: 'none',
                  background:
                    activeTab === tab.id ? 'rgba(16,185,129,0.12)' : 'transparent',
                  color: activeTab === tab.id ? '#34d399' : '#64748b',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  fontFamily: 'inherit',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Main Content */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 360px',
              gap: 24,
              alignItems: 'start',
            }}
          >
            {/* Left Panel */}
            <div
              style={{
                background: 'rgba(15,23,42,0.6)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 20,
                padding: '28px',
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
              }}
            >
              {activeTab === 'pipeline' && <PipelineProgress steps={steps} />}
              {activeTab === 'logs' && <LogStream logs={logs} isRunning={isRunning} />}
              {activeTab === 'tokens' && (
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
                    📊 Token Analysis
                  </h3>
                  {tokenData.length > 0 ? (
                    <TokenPieChart data={tokenData} title="Tokens by Model" />
                  ) : (
                    <div style={{ color: '#64748b', fontSize: 14 }}>
                      No token usage recorded for this project yet.
                    </div>
                  )}
                </div>
              )}
              {activeTab === 'vuln' && (
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
                    🛡️ Vulnerability Scan Results
                  </h3>

                  {vulnSummary ? (
                    <div
                      style={{
                        padding: '16px',
                        background: 'rgba(16,185,129,0.06)',
                        border: '1px solid rgba(16,185,129,0.2)',
                        borderRadius: 12,
                        marginBottom: 20,
                        fontSize: 13.5,
                        color: '#94a3b8',
                        lineHeight: 1.7,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {vulnSummary}
                    </div>
                  ) : (
                    <div
                      style={{
                        padding: '16px',
                        background: 'rgba(255,255,255,0.02)',
                        border: '1px dashed rgba(255,255,255,0.07)',
                        borderRadius: 12,
                        marginBottom: 20,
                        fontSize: 13.5,
                        color: '#475569',
                        textAlign: 'center',
                      }}
                    >
                      {steps.length === 0
                        ? 'Vulnerability scan results will appear here once the pipeline runs.'
                        : 'No vulnerability scan data received yet.'}
                    </div>
                  )}

                  {vulnUpdates.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {vulnUpdates.map((u, i) => (
                        <div
                          key={i}
                          style={{
                            padding: '16px',
                            background: 'rgba(255,255,255,0.02)',
                            border: '1px solid rgba(255,255,255,0.05)',
                            borderRadius: 10,
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              marginBottom: 8,
                            }}
                          >
                            <span
                              style={{
                                fontSize: 13,
                                fontWeight: 700,
                                color: '#e2e8f0',
                                fontFamily: 'JetBrains Mono, monospace',
                              }}
                            >
                              {u.dep}
                            </span>
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: '2px 8px',
                                borderRadius: 100,
                                background: 'rgba(16,185,129,0.1)',
                                color: '#34d399',
                                border: '1px solid rgba(16,185,129,0.25)',
                              }}
                            >
                              ✓ Updated
                            </span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                            <span
                              style={{
                                color: '#ef4444',
                                fontFamily: 'JetBrains Mono, monospace',
                              }}
                            >
                              {u.from_ver}
                            </span>
                            <svg
                              width="12"
                              height="12"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="#475569"
                              strokeWidth="2"
                            >
                              <path d="M5 12h14M12 5l7 7-7 7" />
                            </svg>
                            <span
                              style={{
                                color: '#34d399',
                                fontFamily: 'JetBrains Mono, monospace',
                              }}
                            >
                              {u.to_ver}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right Sidebar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Pipeline summary */}
              <div
                style={{
                  background: 'rgba(15,23,42,0.6)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 20,
                  padding: '24px',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                }}
              >
                <h3
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    marginBottom: 16,
                    color: '#94a3b8',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Pipeline Summary
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {[
                    {
                      label: 'Steps Completed',
                      value:
                        steps.length === 0
                          ? '—'
                          : `${steps.filter((s) => s.status === 'completed').length} / ${steps.length}`,
                      color: '#10b981',
                    },
                    {
                      label: 'Build Tool',
                      value: project.project_type.toUpperCase() || '—',
                      color: '#a78bfa',
                    },
                    {
                      label: 'Deps Updated',
                      value: vulnUpdates.length > 0 ? String(vulnUpdates.length) : '—',
                      color: '#fbbf24',
                    },
                    {
                      label: 'Status',
                      value: project.status.charAt(0).toUpperCase() + project.status.slice(1),
                      color: statusColor,
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontSize: 13, color: '#64748b' }}>{item.label}</span>
                      <span style={{ fontSize: 13, fontWeight: 700, color: item.color }}>
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Project metadata */}
              <div
                style={{
                  background: 'rgba(15,23,42,0.6)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 20,
                  padding: '24px',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                }}
              >
                <h3
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    marginBottom: 16,
                    color: '#94a3b8',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Project Info
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 11, color: '#475569', marginBottom: 4 }}>Repository URL</div>
                    <a
                      href={project.git_repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontSize: 12,
                        color: '#60a5fa',
                        fontFamily: 'JetBrains Mono, monospace',
                        textDecoration: 'none',
                        wordBreak: 'break-all',
                        lineHeight: 1.5,
                      }}
                      onMouseEnter={(e) =>
                        ((e.currentTarget as HTMLElement).style.textDecoration = 'underline')
                      }
                      onMouseLeave={(e) =>
                        ((e.currentTarget as HTMLElement).style.textDecoration = 'none')
                      }
                    >
                      {project.git_repo_url}
                    </a>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: '#475569', marginBottom: 4 }}>Project ID</div>
                    <div
                      style={{
                        fontSize: 13,
                        color: '#94a3b8',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      #{project.id}
                    </div>
                  </div>
                </div>
              </div>

              {/* Download button */}
              {project.status === 'success' && (
                <a
                  href={downloadUrl}
                  id="sidebar-download-btn"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                  style={{ width: '100%', justifyContent: 'center', textDecoration: 'none' }}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download Fixed Project
                </a>
              )}

              {/* Running indicator */}
              {isRunning && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '14px 16px',
                    background: 'rgba(245,158,11,0.08)',
                    border: '1px solid rgba(245,158,11,0.25)',
                    borderRadius: 12,
                    fontSize: 13,
                    color: '#fbbf24',
                  }}
                >
                  <div className="loader-dots">
                    <span /><span /><span />
                  </div>
                  Pipeline is running…
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <style>{`
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @media (max-width: 900px) {
          div[style*="360px"] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </>
  );
}
