'use client';
import { useEffect, useRef } from 'react';

export interface LogEntry {
  type: 'trace' | 'info' | 'warn' | 'error' | 'success' | 'delta';
  message: string;
  timestamp?: string;
}

interface Props {
  logs: LogEntry[];
  isRunning: boolean;
}

export default function LogStream({ logs, isRunning }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLineColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return '#34d399';
      case 'error': return '#f87171';
      case 'warn': return '#fbbf24';
      case 'trace': return '#60a5fa';
      default: return '#94a3b8';
    }
  };

  const getPrefix = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return '✓';
      case 'error': return '✗';
      case 'warn': return '⚠';
      case 'trace': return '→';
      default: return '·';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Terminal header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '10px 16px',
          background: 'rgba(2, 6, 23, 0.8)',
          border: '1px solid rgba(16,185,129,0.15)',
          borderRadius: '12px 12px 0 0',
          borderBottom: 'none',
        }}
      >
        <div style={{ display: 'flex', gap: 6 }}>
          {['#ef4444', '#f59e0b', '#10b981'].map((c) => (
            <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.6 }} />
          ))}
        </div>
        <span style={{ fontSize: 12, color: '#475569', fontFamily: 'JetBrains Mono, monospace', flex: 1, textAlign: 'center' }}>
          mavenfix-agent.log
        </span>
        {isRunning && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: '#f59e0b',
                animation: 'pulse-glow 1.5s ease-in-out infinite',
              }}
            />
            <span style={{ fontSize: 11, color: '#f59e0b', fontWeight: 600 }}>LIVE</span>
          </div>
        )}
      </div>

      {/* Log content */}
      <div
        id="log-stream-container"
        className="terminal"
        style={{ borderRadius: '0 0 12px 12px', borderTop: 'none' }}
      >
        {logs.length === 0 ? (
          <div style={{ color: '#334155', fontFamily: 'JetBrains Mono, monospace' }}>
            <span style={{ color: '#10b981' }}>$</span> Waiting for pipeline events...
            {isRunning && <span className="terminal-cursor" />}
          </div>
        ) : (
          logs.map((log, i) => (
            <div
              key={i}
              className="terminal-line"
              style={{ animationDelay: `${i * 0.02}s` }}
            >
              <span style={{ color: getLineColor(log.type), minWidth: 16 }}>
                {getPrefix(log.type)}
              </span>
              {log.timestamp && (
                <span style={{ color: '#334155', fontSize: 11, minWidth: 80 }}>
                  {log.timestamp}
                </span>
              )}
              <span
                className="terminal-text"
                style={{ color: getLineColor(log.type), opacity: log.type === 'delta' ? 0.75 : 1 }}
              >
                {log.message}
              </span>
            </div>
          ))
        )}
        {isRunning && logs.length > 0 && <span className="terminal-cursor" />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
