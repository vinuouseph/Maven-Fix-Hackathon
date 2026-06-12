'use client';
import Navbar from '@/components/Navbar';
import ProjectCard, { Project } from '@/components/ProjectCard';
import AddProjectModal from '@/components/AddProjectModal';
import DeleteConfirmModal from '@/components/DeleteConfirmModal';
import { useEffect, useState, useCallback } from 'react';
import { getAllProjects, deleteProject, ProjectDetailsDTO } from '@/lib/api';

// ─── Component ────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<string>('all');

  // ── Fetch projects ──────────────────────────────────────────────────────────
  const loadProjects = useCallback(async () => {
      console.log("Iam here");
    setLoading(true);
    setError(null);
    try {
      const items: ProjectDetailsDTO[] = await getAllProjects();
      const mapStatus = (statusNum?: number) => {
        switch (statusNum) {
          case 0: return 'pending';
          case 1: return 'active';
          case 2: return 'running';
          case 3: return 'need attention';
          default: return 'pending';
        }
      };

      setProjects(
        items.map((pd) => ({
          id: pd.project_id,
          project_name: pd.project_name,
          project_description: pd.project_description,
          project_type: pd.project_type as 'maven' | 'gradle',
          git_repo_url: pd.git_repo_url,
          status: mapStatus(pd.status) as any, // real status comes from pipeline SSE stream
        }))
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // ── Delete Handler ────────────────────────────────────────────────────────
  const confirmDelete = async () => {
    if (!projectToDelete) return;
    try {
      await deleteProject(projectToDelete.id);
      loadProjects();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete project');
    }
  };

  // ── Derived state ──────────────────────────────────────────────────────────
  const statusCounts = {
    all: projects.length,
    pending: projects.filter((p) => p.status === 'pending').length,
    active: projects.filter((p) => p.status === 'active').length,
    running: projects.filter((p) => p.status === 'running').length,
    'need attention': projects.filter((p) => p.status === 'need attention').length,
  };

  const filtered = projects.filter((p) => {
    const matchSearch =
      p.project_name.toLowerCase().includes(search.toLowerCase()) ||
      (p.project_description ?? '').toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === 'all' || p.status === filter;
    return matchSearch && matchFilter;
  });

  // ── Render helpers ─────────────────────────────────────────────────────────

  const SkeletonCard = () => (
    <div
      style={{
        background: 'rgba(15,23,42,0.6)',
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: 20,
        padding: 24,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      {[80, 50, 100, 60].map((w, i) => (
        <div
          key={i}
          style={{
            height: i === 0 ? 18 : 12,
            width: `${w}%`,
            borderRadius: 6,
            background:
              'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.6s ease-in-out infinite',
          }}
        />
      ))}
      <style>{`
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
      `}</style>
    </div>
  );

  const StatCard = ({
    label,
    value,
    color,
    isLoading,
  }: {
    label: string;
    value: number;
    color: string;
    isLoading: boolean;
  }) => (
    <div
      style={{
        background: 'rgba(15,23,42,0.6)',
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: 16,
        padding: '20px 24px',
        backdropFilter: 'blur(12px)',
      }}
    >
      <div
        style={{
          fontSize: 28,
          fontWeight: 900,
          color: isLoading ? 'transparent' : color,
          marginBottom: 4,
          minHeight: 36,
          background: isLoading
            ? 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)'
            : 'none',
          backgroundSize: '200% 100%',
          animation: isLoading ? 'shimmer 1.6s ease-in-out infinite' : 'none',
          borderRadius: isLoading ? 8 : 0,
          width: isLoading ? 48 : 'auto',
        }}
      >
        {isLoading ? '' : value}
      </div>
      <div style={{ fontSize: 13, color: '#475569', fontWeight: 500 }}>{label}</div>
    </div>
  );

  // ── JSX ────────────────────────────────────────────────────────────────────

  return (
    <>
      <Navbar />
      <main style={{ minHeight: '100vh', paddingTop: 88 }}>
        {/* Background */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: `
              radial-gradient(circle at 20% 20%, rgba(16,185,129,0.06) 0%, transparent 50%),
              radial-gradient(circle at 80% 80%, rgba(6,182,212,0.05) 0%, transparent 50%)
            `,
            pointerEvents: 'none',
            zIndex: 0,
          }}
        />

        <div
          className="container"
          style={{ position: 'relative', zIndex: 1, paddingTop: 32, paddingBottom: 80 }}
        >
          {/* Page Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              marginBottom: 40,
              flexWrap: 'wrap',
              gap: 16,
            }}
          >
            <div>
              <h1
                style={{ fontSize: 32, fontWeight: 900, marginBottom: 6, letterSpacing: '-0.02em' }}
              >
                Projects{' '}
                <span
                  style={{
                    background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  Dashboard
                </span>
              </h1>
              <p style={{ color: '#64748b', fontSize: 15 }}>
                Manage your Maven repositories and track AI fix pipelines.
              </p>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              {/* Refresh button */}
              <button
                id="refresh-projects-btn"
                onClick={loadProjects}
                disabled={loading}
                className="btn btn-ghost btn-sm"
                title="Refresh projects"
                style={{ opacity: loading ? 0.5 : 1 }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  style={{ animation: loading ? 'spin-slow 1s linear infinite' : 'none' }}
                >
                  <polyline points="23 4 23 10 17 10" />
                  <polyline points="1 20 1 14 7 14" />
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                Refresh
              </button>

              <button
                id="add-project-btn"
                onClick={() => setShowModal(true)}
                className="btn btn-primary"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Add Project
              </button>
            </div>
          </div>

          {/* Stats Row */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: 16,
              marginBottom: 32,
            }}
          >
            <StatCard label="Total Projects" value={statusCounts.all} color="#10b981" isLoading={loading} />
            <StatCard label="Pending" value={statusCounts.pending} color="#64748b" isLoading={loading} />
            <StatCard label="Active" value={statusCounts.active} color="#3b82f6" isLoading={loading} />
            <StatCard label="Running" value={statusCounts.running} color="#f59e0b" isLoading={loading} />
            <StatCard label="Need Attention" value={statusCounts['need attention']} color="#ef4444" isLoading={loading} />
          </div>

          {/* Error banner */}
          {error && !loading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '14px 20px',
                background: 'rgba(239,68,68,0.07)',
                border: '1px solid rgba(239,68,68,0.2)',
                borderRadius: 12,
                marginBottom: 24,
                fontSize: 14,
                color: '#fca5a5',
              }}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#ef4444"
                strokeWidth="2.5"
                style={{ flexShrink: 0 }}
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>
                <strong style={{ color: '#f87171' }}>Could not reach the backend.</strong>{' '}
                Make sure the FastAPI server is running at{' '}
                <code
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 12,
                    color: '#94a3b8',
                    background: 'rgba(255,255,255,0.05)',
                    padding: '1px 6px',
                    borderRadius: 4,
                  }}
                >
                  {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                </code>
              </span>
              <button
                onClick={loadProjects}
                style={{
                  marginLeft: 'auto',
                  padding: '6px 14px',
                  borderRadius: 8,
                  border: '1px solid rgba(239,68,68,0.3)',
                  background: 'rgba(239,68,68,0.1)',
                  color: '#f87171',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  whiteSpace: 'nowrap',
                }}
              >
                Retry
              </button>
            </div>
          )}

          {/* Search & Filter — only shown when data loaded */}
          {!loading && !error && projects.length > 0 && (
            <div
              style={{
                display: 'flex',
                gap: 12,
                marginBottom: 32,
                flexWrap: 'wrap',
                alignItems: 'center',
              }}
            >
              {/* Search */}
              <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
                <div
                  style={{
                    position: 'absolute',
                    left: 14,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: '#475569',
                    pointerEvents: 'none',
                  }}
                >
                  <svg
                    width="15"
                    height="15"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                </div>
                <input
                  id="search-projects"
                  className="input"
                  type="text"
                  placeholder="Search projects..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ paddingLeft: 40 }}
                />
              </div>

              {/* Status filter */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {[
                  { label: `All (${statusCounts.all})`, value: 'all' },
                  { label: `Pending (${statusCounts.pending})`, value: 'pending' },
                  { label: `Active (${statusCounts.active})`, value: 'active' },
                  { label: `Running (${statusCounts.running})`, value: 'running' },
                  { label: `Need Attention (${statusCounts['need attention']})`, value: 'need attention' },
                ].map((f) => (
                  <button
                    key={f.value}
                    id={`filter-${f.value}`}
                    onClick={() => setFilter(f.value)}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 8,
                      border:
                        filter === f.value
                          ? '1px solid rgba(16,185,129,0.4)'
                          : '1px solid rgba(255,255,255,0.06)',
                      background:
                        filter === f.value ? 'rgba(16,185,129,0.1)' : 'transparent',
                      color: filter === f.value ? '#34d399' : '#64748b',
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      fontFamily: 'inherit',
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Loading skeletons ── */}
          {loading && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 20,
              }}
            >
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <SkeletonCard key={n} />
              ))}
            </div>
          )}

          {/* ── Projects Grid ── */}
          {!loading && !error && (
            <>
              {filtered.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">
                    <svg
                      width="32"
                      height="32"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="1.5"
                    >
                      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
                    </svg>
                  </div>
                  <h3 style={{ fontSize: 18, fontWeight: 700 }}>
                    {search || filter !== 'all' ? 'No matching projects' : 'No projects yet'}
                  </h3>
                  <p style={{ color: '#64748b', fontSize: 14 }}>
                    {search
                      ? 'Try adjusting your search terms.'
                      : filter !== 'all'
                        ? 'No projects match this status filter.'
                        : 'Add your first Maven repository to get started.'}
                  </p>
                  {!search && filter === 'all' && (
                    <button
                      id="first-project-btn"
                      className="btn btn-primary btn-sm"
                      onClick={() => setShowModal(true)}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                      >
                        <line x1="12" y1="5" x2="12" y2="19" />
                        <line x1="5" y1="12" x2="19" y2="12" />
                      </svg>
                      Add Your First Project
                    </button>
                  )}
                </div>
              ) : (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                    gap: 24,
                  }}
                >
                  {filtered.map((proj) => (
                    <ProjectCard key={proj.id} project={proj} onDelete={(id) => setProjectToDelete(projects.find(p => p.id === id) || null)} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Add Project Modal */}
      {showModal && (
        <AddProjectModal
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false);
            loadProjects(); // re-fetch after adding
          }}
        />
      )}

      {/* Delete Confirm Modal */}
      {projectToDelete && (
        <DeleteConfirmModal
          onClose={() => setProjectToDelete(null)}
          onConfirm={confirmDelete}
          projectName={projectToDelete.project_name}
        />
      )}

      <style>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @media (max-width: 900px) {
          div[style*="repeat(3, 1fr)"] { grid-template-columns: repeat(2, 1fr) !important; }
          div[style*="repeat(5, 1fr)"] { grid-template-columns: repeat(3, 1fr) !important; }
        }
        @media (max-width: 600px) {
          div[style*="repeat(3, 1fr)"] { grid-template-columns: 1fr !important; }
          div[style*="repeat(5, 1fr)"] { grid-template-columns: repeat(2, 1fr) !important; }
        }
      `}</style>
    </>
  );
}
