'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';

const CODE_SNIPPET = `// MavenFix AI — Auto-fix in action
public class OrderService {
  
  private OrderRepository repo;
  
  public OrderService() {
    this.repo = new OrderRepository(); // ✗ Cannot resolve symbol
  }
  
  public List<Order> getOrders() {
    return repo.findAll();
  }
}

// ✓ MavenFix detected 3 errors
// ✓ Scanning pom.xml for vulnerabilities...
// ✓ Patched 2 outdated dependencies
// ✓ Running compiler (iteration 1/20)...
// ✓ AI generating fix for CannotResolveSymbol
// ✓ Patch applied: Created OrderRepository class
// ✓ BUILD SUCCESS — 0 errors`;

export default function HeroSection() {
  const [displayedCode, setDisplayedCode] = useState('');
  const [codeIndex, setCodeIndex] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    if (codeIndex < CODE_SNIPPET.length) {
      const timer = setTimeout(() => {
        setDisplayedCode((prev) => prev + CODE_SNIPPET[codeIndex]);
        setCodeIndex((i) => i + 1);
      }, 18);
      return () => clearTimeout(timer);
    }
  }, [codeIndex, mounted]);

  return (
    <section
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        position: 'relative',
        overflow: 'hidden',
        paddingTop: 100,
        paddingBottom: 60,
      }}
    >
      {/* Background orbs */}
      <div
        className="orb orb-emerald"
        style={{ width: 600, height: 600, top: -100, left: -200, opacity: 0.6 }}
      />
      <div
        className="orb orb-cyan"
        style={{ width: 500, height: 500, top: 200, right: -150, opacity: 0.5 }}
      />
      <div
        className="orb orb-violet"
        style={{ width: 400, height: 400, bottom: -100, left: '30%', opacity: 0.4 }}
      />

      {/* Grid texture */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
          zIndex: 0,
        }}
      />

      <div className="container" style={{ position: 'relative', zIndex: 1, width: '100%' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 64,
            alignItems: 'center',
          }}
        >
          {/* Left — Text */}
          <div style={{ animation: 'fadeInUp 0.7s ease forwards' }}>
            {/* Badge */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 14px',
                background: 'rgba(16,185,129,0.08)',
                border: '1px solid rgba(16,185,129,0.2)',
                borderRadius: 100,
                marginBottom: 28,
              }}
            >
              <span style={{ fontSize: 8, color: '#10b981' }}>●</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#34d399', letterSpacing: '0.06em' }}>
                AI-POWERED MAVEN REPAIR
              </span>
            </div>

            <h1
              style={{
                fontSize: 'clamp(40px, 5.5vw, 68px)',
                fontWeight: 900,
                lineHeight: 1.08,
                marginBottom: 24,
                letterSpacing: '-0.02em',
              }}
            >
              Fix Maven
              <br />
              <span
                style={{
                  background: 'linear-gradient(135deg, #10b981 0%, #06b6d4 50%, #7c3aed 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}
              >
                Errors with AI
              </span>
            </h1>

            <p
              style={{
                fontSize: 18,
                color: '#94a3b8',
                lineHeight: 1.75,
                marginBottom: 40,
                maxWidth: 480,
              }}
            >
              Connect your Git repository. MavenFix&apos;s LangGraph AI agent automatically
              scans vulnerabilities, compiles, detects errors, and applies intelligent
              patches — all without manual intervention.
            </p>

            {/* CTAs */}
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Link
                href="/dashboard"
                className="btn btn-primary"
                style={{
                  height: 52,
                  padding: '0 32px',
                  fontSize: 15,
                  textDecoration: 'none',
                }}
              >
                Go to Dashboard
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
              <Link
                href="/#how-it-works"
                className="btn btn-ghost btn-lg"
                style={{ textDecoration: 'none' }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" />
                </svg>
                See How It Works
              </Link>
            </div>

            {/* Social proof */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 24,
                marginTop: 48,
                paddingTop: 36,
                borderTop: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              {[
                { value: '20x', label: 'Faster fixes' },
                { value: '99%', label: 'Accuracy rate' },
                { value: 'Maven & Gradle', label: 'Build tools supported' },
              ].map((stat) => (
                <div key={stat.label}>
                  <div
                    style={{
                      fontSize: 22,
                      fontWeight: 800,
                      background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      backgroundClip: 'text',
                    }}
                  >
                    {stat.value}
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — Code Preview */}
          <div
            style={{ animation: 'fadeInUp 0.7s ease 0.2s both' }}
            className="hero-code-panel"
          >
            <div
              style={{
                background: '#020617',
                border: '1px solid rgba(16,185,129,0.2)',
                borderRadius: 20,
                overflow: 'hidden',
                boxShadow: '0 0 60px rgba(16,185,129,0.12), 0 24px 60px rgba(0,0,0,0.6)',
              }}
              className="animate-pulse-glow"
            >
              {/* Terminal chrome */}
              <div
                style={{
                  padding: '14px 20px',
                  background: 'rgba(255,255,255,0.03)',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <div style={{ display: 'flex', gap: 7 }}>
                  {['#ef4444', '#f59e0b', '#10b981'].map((c) => (
                    <div key={c} style={{ width: 12, height: 12, borderRadius: '50%', background: c }} />
                  ))}
                </div>
                <div
                  style={{
                    flex: 1,
                    display: 'flex',
                    justifyContent: 'center',
                    fontSize: 12,
                    color: '#475569',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                >
                  mavenfix-agent.log
                </div>
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: '#10b981',
                    boxShadow: '0 0 8px rgba(16,185,129,0.8)',
                    animation: 'pulse-glow 2s ease-in-out infinite',
                  }}
                />
              </div>

              {/* Code content */}
              <div style={{ padding: '24px 20px', minHeight: 380 }}>
                <pre
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 12.5,
                    lineHeight: 1.9,
                    color: '#94a3b8',
                    whiteSpace: 'pre-wrap',
                    margin: 0,
                  }}
                >
                  {displayedCode.split('\n').map((line, i) => {
                    let color = '#94a3b8';
                    if (line.startsWith('// ✓')) color = '#10b981';
                    else if (line.startsWith('// ✗') || line.includes('// ✗')) color = '#f87171';
                    else if (line.startsWith('@')) color = '#a78bfa';
                    else if (line.startsWith('public') || line.startsWith('  public')) color = '#60a5fa';
                    else if (line.startsWith('//')) color = '#475569';
                    else if (line.includes('@Autowired')) color = '#a78bfa';
                    return (
                      <span key={i} style={{ color, display: 'block' }}>
                        {line}
                      </span>
                    );
                  })}
                  {codeIndex < CODE_SNIPPET.length && <span className="terminal-cursor" />}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .hero-code-panel { display: none; }
          .container > div { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </section>
  );
}
