'use client';

const TECH = [
  { name: 'FastAPI', desc: 'Python async backend', color: '#10b981', icon: '⚡' },
  { name: 'LangGraph', desc: 'Stateful AI pipeline', color: '#a78bfa', icon: '🔗' },
  { name: 'LangChain', desc: 'LLM orchestration', color: '#06b6d4', icon: '🧠' },
  { name: 'Apache Kafka', desc: 'Event streaming', color: '#f59e0b', icon: '📨' },
  { name: 'SQLAlchemy', desc: 'Database ORM', color: '#10b981', icon: '🗄️' },
  { name: 'OpenAI / Anthropic', desc: 'AI models', color: '#a78bfa', icon: '🤖' },
  { name: 'APScheduler', desc: 'Background jobs', color: '#06b6d4', icon: '⏱️' },
  { name: 'Maven', desc: 'Build tool', color: '#f59e0b', icon: '🔧' },
];

export default function TechStack() {
  return (
    <section id="tech-stack" className="section">
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <div className="section-label" style={{ justifyContent: 'center' }}>
            Technology
          </div>
          <h2 className="section-title">
            Built on an <span className="gradient-text">enterprise stack</span>
          </h2>
          <p className="section-subtitle" style={{ margin: '0 auto' }}>
            MavenFix is powered by battle-tested, production-grade technologies used
            by leading engineering teams worldwide.
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 16,
          }}
        >
          {TECH.map((t, i) => (
            <div
              key={i}
              style={{
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 16,
                padding: '24px 20px',
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                cursor: 'default',
                transition: 'all 0.25s ease',
                animation: `fadeInUp 0.4s ease ${i * 0.06}s both`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = t.color + '40';
                e.currentTarget.style.background = `${t.color}08`;
                e.currentTarget.style.transform = 'translateY(-3px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
                e.currentTarget.style.background = 'rgba(15, 23, 42, 0.5)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 12,
                  background: `${t.color}15`,
                  border: `1px solid ${t.color}30`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 20,
                  flexShrink: 0,
                }}
              >
                {t.icon}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#e2e8f0', marginBottom: 2 }}>
                  {t.name}
                </div>
                <div style={{ fontSize: 12, color: '#475569' }}>{t.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          div[style*="repeat(4, 1fr)"] { grid-template-columns: repeat(2, 1fr) !important; }
        }
        @media (max-width: 480px) {
          div[style*="repeat(4, 1fr)"] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </section>
  );
}
