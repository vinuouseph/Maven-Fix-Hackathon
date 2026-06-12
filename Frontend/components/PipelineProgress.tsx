'use client';

export interface PipelineStep {
  id: string;
  title: string;
  detail: string;
  status: 'pending' | 'running' | 'completed' | 'warning' | 'error';
}

const STATUS_ICONS = {
  pending: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
  ),
  running: (
    <div
      style={{
        width: 14,
        height: 14,
        border: '2px solid #f59e0b',
        borderTop: '2px solid transparent',
        borderRadius: '50%',
        animation: 'spin-slow 0.8s linear infinite',
      }}
    />
  ),
  completed: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  warning: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth="2.5">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  error: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  ),
};

const STATUS_COLORS = {
  pending: { icon: '#334155', bg: 'rgba(255,255,255,0.03)', border: 'rgba(255,255,255,0.06)' },
  running: { icon: '#f59e0b', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.3)' },
  completed: { icon: '#10b981', bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.25)' },
  warning: { icon: '#f97316', bg: 'rgba(249,115,22,0.08)', border: 'rgba(249,115,22,0.25)' },
  error: { icon: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.25)' },
};

interface Props {
  steps: PipelineStep[];
}

export default function PipelineProgress({ steps }: Props) {
  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const progress = steps.length > 0 ? (completedCount / steps.length) * 100 : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Progress bar */}
      {steps.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 8,
            }}
          >
            <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>Pipeline Progress</span>
            <span style={{ fontSize: 12, color: '#10b981', fontWeight: 700 }}>
              {completedCount}/{steps.length} steps
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {steps.length === 0 ? (
          <div
            style={{
              padding: '40px 24px',
              textAlign: 'center',
              color: '#334155',
              fontSize: 14,
              border: '1px dashed rgba(255,255,255,0.06)',
              borderRadius: 12,
            }}
          >
            <div style={{ fontSize: 28, marginBottom: 8 }}>⏳</div>
            Waiting for pipeline to start...
          </div>
        ) : (
          steps.map((step, i) => {
            const cfg = STATUS_COLORS[step.status];
            return (
              <div key={step.id + i} style={{ display: 'flex', gap: 0, position: 'relative' }}>
                {/* Left column: icon + connector */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    width: 40,
                    flexShrink: 0,
                  }}
                >
                  {/* Icon circle */}
                  <div
                    className={`pipeline-step-icon ${step.status}`}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      background: cfg.bg,
                      border: `2px solid ${cfg.border}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      zIndex: 1,
                      transition: 'all 0.3s ease',
                    }}
                  >
                    {STATUS_ICONS[step.status]}
                  </div>
                  {/* Connector line */}
                  {i < steps.length - 1 && (
                    <div
                      style={{
                        width: 2,
                        flex: 1,
                        minHeight: 20,
                        background:
                          step.status === 'completed'
                            ? 'linear-gradient(to bottom, rgba(16,185,129,0.4), rgba(16,185,129,0.1))'
                            : 'rgba(255,255,255,0.05)',
                        transition: 'background 0.3s ease',
                      }}
                    />
                  )}
                </div>

                {/* Step content */}
                <div
                  style={{
                    flex: 1,
                    padding: '6px 12px 20px',
                    minWidth: 0,
                  }}
                >
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color:
                        step.status === 'pending'
                          ? '#475569'
                          : step.status === 'completed'
                          ? '#e2e8f0'
                          : '#f1f5f9',
                      marginBottom: 2,
                      transition: 'color 0.3s ease',
                    }}
                  >
                    {step.title}
                  </div>
                  {step.detail && (
                    <div
                      style={{
                        fontSize: 12.5,
                        color: '#475569',
                        lineHeight: 1.5,
                        fontFamily: step.detail.startsWith('Running') ? 'JetBrains Mono, monospace' : 'inherit',
                      }}
                    >
                      {step.detail}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <style>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
