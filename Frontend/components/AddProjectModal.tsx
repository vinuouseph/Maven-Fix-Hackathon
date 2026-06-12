'use client';
import { useState } from 'react';
import { addProject, GitRepoDTO } from '@/lib/api';

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function AddProjectModal({ onClose, onSuccess }: Props) {
  const [form, setForm] = useState<GitRepoDTO>({
    project_name: '',
    project_description: '',
    project_type: 'maven',
    git_repo_url: '',
    build_args: '',
  });
  
  const [scheduleMode, setScheduleMode] = useState<'none' | 'daily' | 'weekly'>('none');
  const [scheduleTime, setScheduleTime] = useState('21:00'); // default 9 PM
  const [scheduleDay, setScheduleDay] = useState('0'); // 0 = Monday for cron

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    let schedule_type = undefined;
    let schedule_config = undefined;
    
    if (scheduleMode !== 'none') {
      schedule_type = 'cron';
      const [hour, minute] = scheduleTime.split(':');
      const configObj: any = { hour: parseInt(hour, 10), minute: parseInt(minute, 10) };
      if (scheduleMode === 'weekly') {
        configObj.day_of_week = parseInt(scheduleDay, 10);
      }
      schedule_config = JSON.stringify(configObj);
    }
    
    try {
      await addProject({
        ...form,
        project_description: form.project_description || undefined,
        build_args: form.build_args || undefined,
        schedule_type,
        schedule_config,
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to add project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 28,
          }}
        >
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>Add New Project</h2>
            <p style={{ fontSize: 13, color: '#64748b' }}>
              MavenFix will clone your repo and begin the fix pipeline automatically.
            </p>
          </div>
          <button
            onClick={onClose}
            id="modal-close"
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: '#64748b',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.color = '#f1f5f9';
              (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.08)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.color = '#64748b';
              (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Project Name */}
          <div>
            <label className="input-label" htmlFor="project-name">Project Name *</label>
            <input
              id="project-name"
              className="input"
              type="text"
              placeholder="e.g. my-maven-app"
              value={form.project_name}
              onChange={(e) => setForm({ ...form, project_name: e.target.value })}
              required
              maxLength={20}
            />
          </div>

          {/* Project Type */}
          <div>
            <label className="input-label">Build Tool *</label>
            <div style={{ display: 'flex', gap: 10 }}>
              {(['maven', 'gradle'] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  id={`build-tool-${type}`}
                  onClick={() => setForm({ ...form, project_type: type })}
                  style={{
                    flex: 1,
                    padding: '12px',
                    borderRadius: 10,
                    border: form.project_type === type
                      ? '1px solid rgba(16,185,129,0.5)'
                      : '1px solid rgba(255,255,255,0.06)',
                    background: form.project_type === type
                      ? 'rgba(16,185,129,0.1)'
                      : 'rgba(255,255,255,0.02)',
                    color: form.project_type === type ? '#34d399' : '#64748b',
                    cursor: 'pointer',
                    fontSize: 14,
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    transition: 'all 0.2s',
                    fontFamily: 'inherit',
                  }}
                >
                  <span>{type === 'maven' ? '🏗️' : '🐘'}</span>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Git Repo URL */}
          <div>
            <label className="input-label" htmlFor="git-url">Git Repository URL *</label>
            <input
              id="git-url"
              className="input"
              type="text"
              placeholder="https://github.com/user/app.git  or  git@host:user/app"
              value={form.git_repo_url}
              onChange={(e) => setForm({ ...form, git_repo_url: e.target.value })}
              required
              style={{ fontFamily: form.git_repo_url.startsWith('git@') ? 'JetBrains Mono, monospace' : 'inherit', fontSize: form.git_repo_url.startsWith('git@') ? 12.5 : 14 }}
            />
            <p style={{ fontSize: 11, color: '#475569', marginTop: 5 }}>
              Supports HTTPS and SSH formats (e.g.&nbsp;
              <code style={{ fontFamily: 'JetBrains Mono, monospace', color: '#64748b' }}>git@host:org/repo</code>)
            </p>
          </div>

          {/* Schedule Options */}
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: 16, borderRadius: 12, border: '1px solid rgba(255,255,255,0.04)' }}>
            <label className="input-label">Fix Pipeline Schedule</label>
            <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
              {(['none', 'daily', 'weekly'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setScheduleMode(mode)}
                  style={{
                    flex: 1,
                    padding: '8px',
                    borderRadius: 8,
                    border: scheduleMode === mode
                      ? '1px solid rgba(59,130,246,0.5)'
                      : '1px solid rgba(255,255,255,0.06)',
                    background: scheduleMode === mode
                      ? 'rgba(59,130,246,0.1)'
                      : 'rgba(255,255,255,0.02)',
                    color: scheduleMode === mode ? '#60a5fa' : '#64748b',
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: 600,
                    textTransform: 'capitalize',
                    transition: 'all 0.2s',
                  }}
                >
                  {mode}
                </button>
              ))}
            </div>

            {scheduleMode !== 'none' && (
              <div style={{ display: 'flex', gap: 12 }}>
                {scheduleMode === 'weekly' && (
                  <div style={{ flex: 1 }}>
                    <label className="input-label" style={{ fontSize: 11 }}>Day of Week</label>
                    <select
                      className="input"
                      value={scheduleDay}
                      onChange={(e) => setScheduleDay(e.target.value)}
                      style={{ padding: '8px 12px', height: 'auto' }}
                    >
                      <option value="0">Monday</option>
                      <option value="1">Tuesday</option>
                      <option value="2">Wednesday</option>
                      <option value="3">Thursday</option>
                      <option value="4">Friday</option>
                      <option value="5">Saturday</option>
                      <option value="6">Sunday</option>
                    </select>
                  </div>
                )}
                <div style={{ flex: 1 }}>
                  <label className="input-label" style={{ fontSize: 11 }}>Time</label>
                  <input
                    type="time"
                    className="input"
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                    style={{ padding: '8px 12px', height: 'auto' }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Build Args */}
          <div>
            <label className="input-label" htmlFor="build-args">Extra Build Arguments (optional)</label>
            <input
              id="build-args"
              className="input"
              type="text"
              placeholder="e.g. -DnewTag=1.0"
              value={form.build_args}
              onChange={(e) => setForm({ ...form, build_args: e.target.value })}
            />
          </div>

          {/* Description */}
          <div>
            <label className="input-label" htmlFor="project-desc">Description (optional)</label>
            <textarea
              id="project-desc"
              className="input"
              placeholder="Brief description of the project..."
              value={form.project_description}
              onChange={(e) => setForm({ ...form, project_description: e.target.value })}
              rows={3}
              maxLength={100}
              style={{ resize: 'vertical', minHeight: 80 }}
            />
          </div>

          {/* Error */}
          {error && (
            <div
              style={{
                padding: '12px 16px',
                background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.25)',
                borderRadius: 10,
                color: '#f87171',
                fontSize: 13,
                display: 'flex',
                gap: 8,
                alignItems: 'center',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          )}

          {/* Submit */}
          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost"
              style={{ flex: 1 }}
            >
              Cancel
            </button>
            <button
              type="submit"
              id="submit-add-project"
              disabled={loading}
              className="btn btn-primary"
              style={{ flex: 2, opacity: loading ? 0.7 : 1 }}
            >
              {loading ? (
                <>
                  <div className="loader-dots">
                    <span /><span /><span />
                  </div>
                  Adding...
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  Add Project
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
