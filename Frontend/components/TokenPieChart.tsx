'use client';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

interface TokenUsageItem {
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

interface TokenPieChartProps {
  data: TokenUsageItem[];
  title?: string;
}

export default function TokenPieChart({ data, title }: TokenPieChartProps) {
  if (!data || data.length === 0) {
    return <div style={{ padding: 16, textAlign: 'center', color: '#64748b' }}>No token data available.</div>;
  }

  // Format data for Recharts
  const chartData = data.flatMap((item) => [
    {
      name: `${item.model_name} (Input)`,
      value: item.input_tokens,
      originalName: item.model_name,
      type: 'Input'
    },
    {
      name: `${item.model_name} (Output)`,
      value: item.output_tokens,
      originalName: item.model_name,
      type: 'Output'
    }
  ]).filter((d) => d.value > 0);

  return (
    <div style={{
      width: '100%',
      height: 320,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      background: 'rgba(15,23,42,0.6)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 20,
      padding: 24,
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
    }}>
      {title && <h3 style={{ fontSize: 16, fontWeight: 700, color: '#e2e8f0', marginBottom: 16 }}>{title}</h3>}
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={5}
            dataKey="value"
            label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip 
            formatter={(value: any, name: any, props: any) => [
              `${value} Tokens`, 
              name
            ]}
          />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
