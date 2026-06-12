'use client';
import Link from 'next/link';

export default function CTASection() {
  return (
    <section className="section" style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Orbs */}
      <div className="orb orb-emerald" style={{ width: 500, height: 500, top: -100, left: -100, opacity: 0.5 }} />
      <div className="orb orb-cyan" style={{ width: 400, height: 400, bottom: -80, right: -80, opacity: 0.4 }} />

      <div className="container" style={{ position: 'relative', zIndex: 1 }}>
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(6,182,212,0.06) 50%, rgba(124,58,237,0.06) 100%)',
            border: '1px solid rgba(16,185,129,0.2)',
            borderRadius: 32,
            padding: '80px 64px',
            textAlign: 'center',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            boxShadow: '0 0 80px rgba(16,185,129,0.08), inset 0 1px 0 rgba(255,255,255,0.05)',
          }}
        >
          {/* Badge */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 16px',
              background: 'rgba(16,185,129,0.1)',
              border: '1px solid rgba(16,185,129,0.25)',
              borderRadius: 100,
              marginBottom: 28,
              fontSize: 12,
              fontWeight: 600,
              color: '#34d399',
              letterSpacing: '0.06em',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
            GET STARTED TODAY
          </div>

          <h2
            style={{
              fontSize: 'clamp(32px, 5vw, 56px)',
              fontWeight: 900,
              lineHeight: 1.1,
              marginBottom: 20,
              letterSpacing: '-0.02em',
            }}
          >
            Ready to fix your{' '}
            <span
              style={{
                background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              Maven project?
            </span>
          </h2>

          <p
            style={{
              fontSize: 18,
              color: '#64748b',
              marginBottom: 48,
              maxWidth: 560,
              margin: '0 auto 48px',
              lineHeight: 1.7,
            }}
          >
            Add your repository URL and let MavenFix&apos;s AI agent handle the rest —
            from vulnerability scanning to iterative compilation fixes.
          </p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link
              href="/dashboard"
              id="cta-go-to-dashboard"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 10,
                padding: '16px 36px',
                background: 'linear-gradient(135deg, #10b981, #059669)',
                color: 'white',
                borderRadius: 14,
                textDecoration: 'none',
                fontSize: 16,
                fontWeight: 700,
                boxShadow: '0 8px 32px rgba(16,185,129,0.4)',
                transition: 'all 0.25s ease',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(-3px)';
                (e.currentTarget as HTMLElement).style.boxShadow = '0 16px 48px rgba(16,185,129,0.5)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
                (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 32px rgba(16,185,129,0.4)';
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
              </svg>
              Open Dashboard
            </Link>

            <a
              href="#features"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 10,
                padding: '16px 36px',
                background: 'transparent',
                color: '#94a3b8',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 14,
                textDecoration: 'none',
                fontSize: 16,
                fontWeight: 600,
                transition: 'all 0.25s ease',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.2)';
                (e.currentTarget as HTMLElement).style.color = '#f1f5f9';
                (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.1)';
                (e.currentTarget as HTMLElement).style.color = '#94a3b8';
                (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
            >
              View Features
            </a>
          </div>

          {/* Feature bullets */}
          <div
            style={{
              display: 'flex',
              gap: 32,
              justifyContent: 'center',
              marginTop: 48,
              flexWrap: 'wrap',
            }}
          >
            {['No credit card required', 'Maven support', 'Real-time AI pipeline'].map(
              (item) => (
                <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      background: 'rgba(16,185,129,0.15)',
                      border: '1px solid rgba(16,185,129,0.3)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                  <span style={{ fontSize: 13, color: '#64748b' }}>{item}</span>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
