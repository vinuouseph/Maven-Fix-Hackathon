'use client';
import { motion } from 'framer-motion';
import { 

  ShieldCheck, FileJson, AlertTriangle, Hammer, ListTree, 
  CheckCircle, Cpu, XCircle, Bot, AlertCircle, FileText, FileEdit, FilePlus,
  FolderUp, Network, HardDriveDownload
} from 'lucide-react';
import { useEffect, useState } from 'react';

type NodeDef = {
  id: string;
  x: number;
  y: number;
  label: string;
  desc: string;
  icon: any;
  color: string;
  isTool?: boolean;
};

const NODES: NodeDef[] = [
  // Platform / Infra
  { id: 'upload', x: 500, y: 100, label: 'Add Project', desc: 'UI & FastAPI Endpoint', icon: FolderUp, color: '#a855f7' },
  { id: 'kafka', x: 500, y: 300, label: 'Kafka Broker', desc: 'Message Queue', icon: Network, color: '#f97316' },
  { id: 'worker', x: 500, y: 500, label: 'FastStream Worker', desc: 'Consumes event & clones Git repo', icon: HardDriveDownload, color: '#14b8a6' },

  // LangGraph Pipeline
  { id: 'pre_check', x: 500, y: 700, label: 'Pre-Compile Check', desc: 'Validates workspace & POM', icon: ShieldCheck, color: '#3b82f6' },
  { id: 'pom_update', x: 250, y: 900, label: 'POM Update', desc: 'Injects required plugins', icon: FileJson, color: '#8b5cf6' },
  { id: 'pre_esc', x: 750, y: 900, label: 'Pre-Compile Escalate', desc: 'Fails on missing POM', icon: AlertTriangle, color: '#f59e0b' },
  { id: 'compile', x: 500, y: 1100, label: 'Compile', desc: 'Runs Maven compiler', icon: Hammer, color: '#10b981' },
  { id: 'parse', x: 500, y: 1300, label: 'Parse Errors', desc: 'Extracts compiler logs', icon: ListTree, color: '#6366f1' },
  { id: 'success', x: 200, y: 1500, label: 'Success', desc: 'Build passed', icon: CheckCircle, color: '#10b981' },
  { id: 'context', x: 500, y: 1500, label: 'Build Context', desc: 'Gather files for LLM', icon: Cpu, color: '#ec4899' },
  { id: 'abort', x: 800, y: 1500, label: 'Abort', desc: 'Max iterations reached', icon: XCircle, color: '#ef4444' },
  { id: 'llm', x: 250, y: 1700, label: 'LLM Fix Agent', desc: 'AI writes code patches', icon: Bot, color: '#0ea5e9' },
  { id: 'esc', x: 750, y: 1700, label: 'Escalate', desc: 'LLM failed to apply fix', icon: AlertCircle, color: '#f59e0b' },
  
  // Tools
  { id: 'tool_list', x: 200, y: 1900, label: 'List Files', desc: '', icon: ListTree, color: '#cbd5e1', isTool: true },
  { id: 'tool_read', x: 400, y: 1900, label: 'Read File', desc: '', icon: FileText, color: '#cbd5e1', isTool: true },
  { id: 'tool_write', x: 600, y: 1900, label: 'Write Lines', desc: '', icon: FileEdit, color: '#cbd5e1', isTool: true },
  { id: 'tool_create', x: 800, y: 1900, label: 'Create File', desc: '', icon: FilePlus, color: '#cbd5e1', isTool: true },
];

const EDGES = [
  { from: 'upload', to: 'kafka', type: 'straight' },
  { from: 'kafka', to: 'worker', type: 'straight' },
  { from: 'worker', to: 'pre_check', type: 'straight' },
  
  { from: 'pre_check', to: 'pom_update', type: 'straight' },
  { from: 'pre_check', to: 'pre_esc', type: 'straight' },
  { from: 'pom_update', to: 'compile', type: 'straight' },
  { from: 'compile', to: 'parse', type: 'straight' },
  { from: 'parse', to: 'success', type: 'straight' },
  { from: 'parse', to: 'context', type: 'straight' },
  { from: 'parse', to: 'abort', type: 'straight' },
  { from: 'context', to: 'llm', type: 'straight' },
  { from: 'context', to: 'esc', type: 'straight' },
  
  { from: 'llm', to: 'tool_list', type: 'straight' },
  { from: 'llm', to: 'tool_read', type: 'straight' },
  { from: 'llm', to: 'tool_write', type: 'straight' },
  { from: 'llm', to: 'tool_create', type: 'straight' },
];

export default function ArchitectureGraph() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div style={{ width: '100%', maxWidth: 1200, margin: '0 auto', overflowX: 'auto', padding: '20px 0' }}>
      <div style={{ position: 'relative', width: 1200, height: 2100, margin: '0 auto' }}>
        {/* Edges */}
        <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1 }}>
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255,255,255,0.3)" />
            </marker>
            <marker id="arrowhead-tool" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#0ea5e9" />
            </marker>
          </defs>
          
          {EDGES.map((edge, i) => {
            const from = NODES.find(n => n.id === edge.from)!;
            const to = NODES.find(n => n.id === edge.to)!;
            
            // Always originate from the bottom-center of 'from' and terminate at top-center of 'to'
            const fromYOffset = from.isTool ? 24 : 50;
            const toYOffset = to.isTool ? 24 : 50;
            
            const x1 = from.x;
            const y1 = from.y + fromYOffset;
            const x2 = to.x;
            const y2 = to.y - toYOffset;
            
            const isToolEdge = to.isTool;
            const strokeColor = isToolEdge ? "#0ea5e9" : "rgba(255,255,255,0.2)";
            const strokeWidth = isToolEdge ? "3" : "2";
            const opacity = isToolEdge ? 0.7 : 1;
            
            return (
              <motion.path
                key={i}
                d={`M ${x1} ${y1} C ${x1} ${(y1+y2)/2}, ${x2} ${(y1+y2)/2}, ${x2} ${y2}`}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray={isToolEdge ? "6,6" : "none"}
                fill="none"
                opacity={opacity}
                markerEnd={isToolEdge ? "url(#arrowhead-tool)" : "url(#arrowhead)"}
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: opacity }}
                transition={{ duration: 1.5, delay: i * 0.1, ease: 'easeInOut' }}
              />
            );
          })}
          
          {/* Curved Edge: LLM to Compile (Loop) */}
          {(() => {
            const from = NODES.find(n => n.id === 'llm')!;
            const to = NODES.find(n => n.id === 'compile')!;
            return (
              <motion.path
                d={`M ${from.x} ${from.y} C ${from.x - 300} ${from.y}, ${to.x - 300} ${to.y}, ${to.x - 110} ${to.y}`}
                stroke="#10b981"
                strokeWidth="2"
                strokeDasharray="6,6"
                fill="none"
                markerEnd="url(#arrowhead)"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 0.6 }}
                transition={{ duration: 2, delay: 1.5, ease: 'easeInOut' }}
              />
            );
          })()}
        </svg>

        {/* Nodes */}
        {NODES.map((node, i) => {
          const Icon = node.icon;
          return (
            <motion.div
              key={node.id}
              style={{
                position: 'absolute',
                left: node.x,
                top: node.y,
                transform: 'translate(-50%, -50%)',
                zIndex: 2,
                width: node.isTool ? 140 : 220,
                padding: node.isTool ? '12px' : '16px',
                background: node.isTool ? 'rgba(14, 165, 233, 0.1)' : 'rgba(15, 23, 42, 0.7)',
                backdropFilter: 'blur(12px)',
                border: `1px solid ${node.isTool ? 'rgba(14, 165, 233, 0.3)' : 'rgba(255,255,255,0.08)'}`,
                borderRadius: node.isTool ? 12 : 16,
                display: 'flex',
                flexDirection: node.isTool ? 'row' : 'column',
                alignItems: 'center',
                textAlign: 'center',
                boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                cursor: 'default',
                gap: node.isTool ? 8 : 0,
              }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{
                type: "spring",
                stiffness: 260,
                damping: 20,
                delay: i * 0.1
              }}
              whileHover={{
                scale: 1.05,
                borderColor: node.color,
                boxShadow: `0 0 20px ${node.color}40`,
                background: node.isTool ? 'rgba(14, 165, 233, 0.2)' : 'rgba(15, 23, 42, 0.9)',
              }}
            >
              <div
                style={{
                  width: node.isTool ? 32 : 48,
                  height: node.isTool ? 32 : 48,
                  borderRadius: node.isTool ? 8 : 12,
                  background: `${node.color}15`,
                  color: node.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: node.isTool ? 0 : 12,
                  border: `1px solid ${node.color}30`,
                  flexShrink: 0,
                }}
              >
                <Icon size={node.isTool ? 16 : 24} />
              </div>
              <div style={{ textAlign: node.isTool ? 'left' : 'center' }}>
                <h3 style={{ fontSize: node.isTool ? 12 : 14, fontWeight: 700, color: '#f8fafc', marginBottom: node.isTool ? 0 : 4 }}>
                  {node.label}
                </h3>
                {!node.isTool && (
                  <p style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
                    {node.desc}
                  </p>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
