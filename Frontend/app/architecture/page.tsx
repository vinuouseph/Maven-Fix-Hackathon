import Navbar from '@/components/Navbar';
import ArchitectureGraph from '@/components/ArchitectureGraph';

export default function ArchitecturePage() {
  return (
    <main style={{ minHeight: '100vh', background: '#030712', color: '#f8fafc', paddingTop: 80 }}>
      <Navbar />
      
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 24px' }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 12, background: 'linear-gradient(135deg, #10b981, #06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Pipeline Architecture
          </h1>
          <p style={{ color: '#94a3b8', maxWidth: 600, margin: '0 auto', fontSize: 15, lineHeight: 1.6 }}>
            A visualization of the LangGraph AI workflow powering MavenFix. The system autonomously compiles your project, parses errors, builds context, and writes patches iteratively until the build succeeds.
          </p>
        </div>

        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.05)',
          borderRadius: 24,
          padding: 20,
          boxShadow: 'inset 0 0 40px rgba(0,0,0,0.5)',
        }}>
          <ArchitectureGraph />
        </div>
      </div>
    </main>
  );
}
