'use client';

import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import TokenPieChart from '@/components/TokenPieChart';
import { API_BASE } from '@/lib/api';

export default function AnalyticsPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/git/token-analysis/total`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch analytics');
        return res.json();
      })
      .then((json) => {
        setData(json.data || []);
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <>
      <Navbar />
      <main style={{ minHeight: '100vh', paddingTop: 88, paddingBottom: 40, background: '#020617', color: '#f8fafc', fontFamily: 'Inter, sans-serif' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px' }}>
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 32, fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              Global Token Analysis
            </h1>
            <p style={{ marginTop: 8, color: '#94a3b8', fontSize: 16 }}>
              View the aggregate total token consumption across all projects by AI models.
            </p>
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 256 }}>
              <div className="loader-dots">
                <span /><span /><span />
              </div>
            </div>
          ) : error ? (
            <div style={{ padding: 16, background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 12 }}>
              {error}
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32, alignItems: 'start' }}>
              <TokenPieChart data={data} title="Total Tokens by Model" />
              
              <div style={{ 
                background: 'rgba(15,23,42,0.6)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 20,
                padding: 24,
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
              }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#e2e8f0', marginBottom: 16 }}>Detailed Breakdown</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 14 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 600 }}>Model</th>
                        <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 600 }}>Input Tokens</th>
                        <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 600 }}>Output Tokens</th>
                        <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 600, textAlign: 'right' }}>Total Tokens</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.length === 0 ? (
                        <tr>
                          <td colSpan={4} style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b' }}>
                            No token usage recorded yet.
                          </td>
                        </tr>
                      ) : (
                        data.map((item: any) => (
                          <tr key={item.model_name} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                            <td style={{ padding: '12px 16px', fontWeight: 500, color: '#f8fafc' }}>{item.model_name}</td>
                            <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>{item.input_tokens.toLocaleString()}</td>
                            <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>{item.output_tokens.toLocaleString()}</td>
                            <td style={{ padding: '12px 16px', fontWeight: 600, color: '#10b981', textAlign: 'right' }}>
                              {item.total_tokens.toLocaleString()}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
      <style>{`
        @media (max-width: 768px) {
          div[style*="grid-template-columns: 1fr 1fr"] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </>
  );
}
