export const mockEngines = [
  {
    id: 1,
    name: 'Engine 001',
    rul: 142,
    rulHistory: [165, 160, 156, 153, 150, 148, 146, 145, 143, 142],
    healthPercent: 89,
    cycleCount: 87,
    status: 'healthy',
  },
  {
    id: 2,
    name: 'Engine 002',
    rul: 38,
    rulHistory: [65, 60, 54, 50, 46, 44, 42, 40, 39, 38],
    healthPercent: 52,
    cycleCount: 134,
    status: 'warning',
  },
  {
    id: 3,
    name: 'Engine 003',
    rul: 6,
    rulHistory: [28, 24, 20, 17, 14, 11, 9, 8, 7, 6],
    healthPercent: 12,
    cycleCount: 193,
    status: 'critical',
  },
  {
    id: 4,
    name: 'Engine 004',
    rul: 95,
    rulHistory: [112, 110, 108, 105, 103, 101, 99, 97, 96, 95],
    healthPercent: 74,
    cycleCount: 112,
    status: 'healthy',
  },
  {
    id: 5,
    name: 'Engine 005',
    rul: 22,
    rulHistory: [45, 40, 36, 32, 29, 27, 26, 24, 23, 22],
    healthPercent: 35,
    cycleCount: 167,
    status: 'warning',
  },
]

export const statusConfig = {
  healthy:  { label: 'Healthy',  color: '#22c55e', bg: 'rgba(34,197,94,0.1)',  glow: 'rgba(34,197,94,0.12)' },
  caution:  { label: 'Caution',  color: '#f97316', bg: 'rgba(249,115,22,0.1)', glow: 'rgba(249,115,22,0.12)' },
  warning:  { label: 'Warning',  color: '#eab308', bg: 'rgba(234,179,8,0.1)',  glow: 'rgba(234,179,8,0.12)' },
  critical: { label: 'Critical', color: '#ef4444', bg: 'rgba(239,68,68,0.1)',  glow: 'rgba(239,68,68,0.18)' },
}
