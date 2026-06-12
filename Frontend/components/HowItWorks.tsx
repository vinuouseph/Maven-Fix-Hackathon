'use client';

const STEPS = [
  {
    number: '01',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
      </svg>
    ),
    title: 'Add Your Git Repo',
    description:
      'Paste your Maven Git repository URL along with the project name. MavenFix clones it and sets up an isolated workspace.',
    tags: ['Git Clone', 'Maven'],
    color: '#10b981',
  },
  {
    number: '02',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    title: 'Vulnerability Scan & POM Update',
    description:
      'The POM update node scans your pom.xml for outdated and vulnerable dependencies using real CVE data. Safe updates are automatically applied before compilation.',
    tags: ['CVE Scan', 'Dep Update', 'pom.xml'],
    color: '#06b6d4',
  },
  {
    number: '03',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
    title: 'AI-Powered Fix Loop',
    description:
      'The LangGraph agent compiles your project, parses compiler errors, builds a token-efficient context window, then prompts the LLM to inspect and patch source files. This repeats up to 20 iterations.',
    tags: ['LangGraph', 'LLM Fix', 'Max 20 Iterations'],
    color: '#a78bfa',
  },
  {
    number: '04',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
    ),
    title: 'Download Fixed Project',
    description:
      'Once compilation succeeds, the corrected project is archived and made available for immediate download — complete with a detailed fix summary and vulnerability report.',
    tags: ['ZIP Archive', 'Fix Summary', 'Vuln Report'],
    color: '#f59e0b',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="section" style={{ background: 'rgba(6,182,212,0.02)' }}>
      <div className="container">
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 72 }}>
          <div className="section-label" style={{ justifyContent: 'center' }}>
            Process
          </div>
          <h2 className="section-title">
            From broken build to{' '}
            <span className="gradient-text">production ready</span>
          </h2>
          <p className="section-subtitle" style={{ margin: '0 auto' }}>
            A four-step automated pipeline that handles everything from Git cloning to
            a production-ready, vulnerability-free Maven project.
          </p>
        </div>

        {/* Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {STEPS.map((step, i) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 80px 1fr',
                gap: 0,
                alignItems: 'center',
                marginBottom: 0,
              }}
            >
              {/* Left side */}
              <div
                style={{
                  padding: '40px 48px 40px 0',
                  textAlign: 'right',
                  opacity: 0,
                  animation: `fadeInUp 0.5s ease ${i * 0.15}s forwards`,
                }}
              >
                {i % 2 === 0 && (
                  <StepContent step={step} align="right" />
                )}
              </div>

              {/* Center line */}
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  position: 'relative',
                }}
              >
                {/* Line top */}
                {i > 0 && (
                  <div style={{ width: 2, height: 40, background: 'linear-gradient(to bottom, rgba(16,185,129,0.3), rgba(16,185,129,0.1))' }} />
                )}

                {/* Step bubble */}
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: '50%',
                    background: `linear-gradient(135deg, ${step.color}22, ${step.color}11)`,
                    border: `2px solid ${step.color}50`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: step.color,
                    zIndex: 1,
                    flexShrink: 0,
                    boxShadow: `0 0 24px ${step.color}25`,
                  }}
                >
                  {step.icon}
                </div>

                {/* Line bottom */}
                {i < STEPS.length - 1 && (
                  <div style={{ width: 2, height: 40, background: 'linear-gradient(to bottom, rgba(16,185,129,0.1), rgba(16,185,129,0.3))' }} />
                )}
              </div>

              {/* Right side */}
              <div
                style={{
                  padding: '40px 0 40px 48px',
                  textAlign: 'left',
                  opacity: 0,
                  animation: `fadeInUp 0.5s ease ${i * 0.15 + 0.1}s forwards`,
                }}
              >
                {i % 2 === 1 && (
                  <StepContent step={step} align="left" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          div[style*="1fr 80px 1fr"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </section>
  );
}

function StepContent({
  step,
  align,
}: {
  step: (typeof STEPS)[0];
  align: 'left' | 'right';
}) {
  return (
    <div>
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.15em',
          color: step.color,
          marginBottom: 8,
          opacity: 0.7,
          textAlign: align,
        }}
      >
        STEP {step.number}
      </div>
      <h3
        style={{
          fontSize: 22,
          fontWeight: 800,
          marginBottom: 12,
          color: '#f1f5f9',
          textAlign: align,
        }}
      >
        {step.title}
      </h3>
      <p
        style={{
          fontSize: 14.5,
          color: '#64748b',
          lineHeight: 1.75,
          marginBottom: 16,
          maxWidth: 360,
          marginLeft: align === 'right' ? 'auto' : 0,
          textAlign: align,
        }}
      >
        {step.description}
      </p>
      <div
        style={{
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
          justifyContent: align === 'right' ? 'flex-end' : 'flex-start',
        }}
      >
        {step.tags.map((tag) => (
          <span
            key={tag}
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '3px 10px',
              borderRadius: 100,
              background: `${step.color}12`,
              border: `1px solid ${step.color}30`,
              color: step.color,
            }}
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
