import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { statusConfig } from '../data/mockEngines'

export default function RULChart({ engine }) {
  const cfg = statusConfig[engine.status]

  const data = engine.rulHistory.map((rul, i) => ({
    cycle: engine.cycleCount - (engine.rulHistory.length - 1 - i),
    rul,
  }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="rulGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={cfg.color} stopOpacity={0.2} />
            <stop offset="100%" stopColor={cfg.color} stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid stroke="#1e1e2e" strokeDasharray="4 4" vertical={false} />

        <XAxis
          dataKey="cycle"
          tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'Inter' }}
          axisLine={false}
          tickLine={false}
          label={{ value: 'Cycle', position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 11 }}
        />

        <YAxis
          tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'Inter' }}
          axisLine={false}
          tickLine={false}
          label={{ value: 'RUL', angle: -90, position: 'insideLeft', offset: 20, fill: '#64748b', fontSize: 11 }}
        />

        <Tooltip
          contentStyle={{
            backgroundColor: '#111118',
            border: '1px solid #1e1e2e',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#e2e8f0',
          }}
          formatter={(value) => [`${value} cycles`, 'RUL']}
          labelFormatter={(label) => `Cycle ${label}`}
        />

        <ReferenceLine
          y={50}
          stroke="#eab308"
          strokeDasharray="4 4"
          strokeOpacity={0.5}
          label={{ value: 'Alert', fill: '#eab308', fontSize: 10, position: 'right' }}
        />

        <Line
          type="monotone"
          dataKey="rul"
          stroke={cfg.color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: cfg.color, strokeWidth: 0 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
