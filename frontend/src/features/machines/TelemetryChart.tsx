import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend 
} from 'recharts';
import type { TelemetryPoint } from '../../types/machine';

interface TelemetryChartProps {
  data: TelemetryPoint[];
  title?: string;
}

const TelemetryChart: React.FC<TelemetryChartProps> = ({ data, title }) => {
  return (
    <div style={{ width: '100%', height: 300, backgroundColor: 'var(--bg-secondary)', padding: '1rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      {title && <h4 style={{ marginBottom: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{title}</h4>}
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
          <XAxis 
            dataKey="timestamp" 
            stroke="var(--text-muted)" 
            fontSize={12} 
            tickLine={false} 
            axisLine={false} 
          />
          <YAxis 
            stroke="var(--text-muted)" 
            fontSize={12} 
            tickLine={false} 
            axisLine={false}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
            itemStyle={{ fontSize: '0.75rem' }}
          />
          <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }} />
          <Line 
            type="monotone" 
            dataKey="processTemperature" 
            stroke="var(--status-critical)" 
            strokeWidth={2} 
            dot={false} 
            name="Temp. Processo (K)"
          />
          <Line 
            type="monotone" 
            dataKey="airTemperature" 
            stroke="var(--brand-primary)" 
            strokeWidth={2} 
            dot={false} 
            name="Temp. Ar (K)"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TelemetryChart;
