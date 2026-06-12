'use client';
import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import { getAllSchedules } from '@/lib/api';

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAllSchedules()
      .then((data) => {
        setSchedules(data);
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const formatConfig = (type: string, configStr: string) => {
    try {
      const conf = JSON.parse(configStr);
      if (type === 'cron') {
        const hour = conf.hour?.toString().padStart(2, '0') || '00';
        const minute = conf.minute?.toString().padStart(2, '0') || '00';
        let res = `Daily at ${hour}:${minute}`;
        if (conf.day_of_week !== undefined) {
          const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
          res = `Weekly on ${days[conf.day_of_week]} at ${hour}:${minute}`;
        }
        return res;
      }
      return configStr;
    } catch {
      return configStr;
    }
  };

  return (
    <>
      <Navbar />
      <main style={{ minHeight: '100vh', paddingTop: 88, paddingBottom: 40, background: '#020617', color: '#f8fafc', fontFamily: 'Inter, sans-serif' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px' }}>
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 32, fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              Project Schedules
            </h1>
            <p style={{ marginTop: 8, color: '#94a3b8', fontSize: 16 }}>
              Track the automated git pulling and fixing schedules.
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
          ) : schedules.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 20 }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>⏰</div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 }}>No schedules active</h3>
              <p style={{ color: '#94a3b8' }}>Add a project with a schedule to see it here.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: 24 }}>
              {schedules.map((sched) => (
                <div key={sched.id} style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 20, padding: 24, backdropFilter: 'blur(12px)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                    <div>
                      <h3 style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>{sched.project_name}</h3>
                      <div style={{ fontSize: 13, color: '#64748b' }}>Project ID: {sched.project_id}</div>
                    </div>
                    <div style={{ padding: '6px 12px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', borderRadius: 100, color: '#60a5fa', fontSize: 12, fontWeight: 600 }}>
                      Active
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', background: 'rgba(255,255,255,0.02)', borderRadius: 12 }}>
                    <div style={{ fontSize: 20 }}>⏰</div>
                    <div>
                      <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>{sched.schedule_type} Schedule</div>
                      <div style={{ fontSize: 14, color: '#f8fafc', fontWeight: 500 }}>
                        {formatConfig(sched.schedule_type, sched.schedule_config)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
