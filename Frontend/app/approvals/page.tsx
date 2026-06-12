'use client';
import Navbar from '@/components/Navbar';
import { useEffect, useState, useCallback } from 'react';
import { getFixRequests, FixRequestDTO } from '@/lib/api';

export default function ApprovalsPage() {
  const [requests, setRequests] = useState<FixRequestDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRequests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFixRequests();
      setRequests(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load approvals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PENDING': return '#f59e0b';
      case 'APPROVED': return '#10b981';
      case 'REJECTED': return '#ef4444';
      default: return '#64748b';
    }
  };

  return (
    <>
      <Navbar />
      <main style={{ minHeight: '100vh', paddingTop: 88 }}>
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

        <div className="container" style={{ position: 'relative', zIndex: 1, paddingTop: 32, paddingBottom: 80 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 40, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 6, letterSpacing: '-0.02em' }}>
                Fix <span style={{ background: 'linear-gradient(135deg, #10b981, #06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>Approvals</span>
              </h1>
              <p style={{ color: '#64748b', fontSize: 15 }}>
                Track the history of AI project fix approvals and rejections.
              </p>
            </div>
            <div>
              <button onClick={loadRequests} disabled={loading} className="btn btn-ghost btn-sm" title="Refresh approvals" style={{ opacity: loading ? 0.5 : 1 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: loading ? 'spin-slow 1s linear infinite' : 'none' }}>
                  <polyline points="23 4 23 10 17 10" />
                  <polyline points="1 20 1 14 7 14" />
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                Refresh
              </button>
            </div>
          </div>

          {error && !loading && (
            <div style={{ padding: '14px 20px', background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 12, marginBottom: 24, color: '#fca5a5' }}>
              <strong style={{ color: '#f87171' }}>Could not load data.</strong> {error}
            </div>
          )}

          {!loading && !error && requests.length === 0 && (
            <div className="empty-state">
              <h3 style={{ fontSize: 18, fontWeight: 700 }}>No approvals history yet</h3>
              <p style={{ color: '#64748b', fontSize: 14 }}>Once a project is fixed by AI, it will appear here.</p>
            </div>
          )}

          {!loading && !error && requests.length > 0 && (
            <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 16, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <tr>
                    <th style={{ padding: '16px 24px', fontSize: 13, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>ID</th>
                    <th style={{ padding: '16px 24px', fontSize: 13, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Project</th>
                    <th style={{ padding: '16px 24px', fontSize: 13, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Date</th>
                    <th style={{ padding: '16px 24px', fontSize: 13, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map(req => (
                    <tr key={req.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.2s', ':hover': { background: 'rgba(255,255,255,0.01)' } } as any}>
                      <td style={{ padding: '16px 24px', fontSize: 14, color: '#94a3b8' }}>#{req.id}</td>
                      <td style={{ padding: '16px 24px', fontSize: 14, fontWeight: 500, color: '#f8fafc' }}>{req.project_name}</td>
                      <td style={{ padding: '16px 24px', fontSize: 14, color: '#cbd5e1' }}>
                        {req.created_at ? new Date(req.created_at).toLocaleString() : 'N/A'}
                      </td>
                      <td style={{ padding: '16px 24px' }}>
                        <span style={{ 
                          padding: '4px 10px', 
                          borderRadius: 20, 
                          fontSize: 12, 
                          fontWeight: 600, 
                          background: `${getStatusColor(req.status)}20`, 
                          color: getStatusColor(req.status),
                          border: `1px solid ${getStatusColor(req.status)}40`
                        }}>
                          {req.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
      <style>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </>
  );
}
