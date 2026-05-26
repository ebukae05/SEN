interface Props {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  threshold?: number;
  thresholdColor?: string;
  yLabel?: string;
  showAxis?: boolean;
}

export function LineChart({
  data,
  width = 800,
  height = 220,
  color = "#C084FC",
  threshold,
  thresholdColor = "#EF4444",
  yLabel,
  showAxis = true,
}: Props) {
  if (data.length === 0) return null;
  const padL = showAxis ? 40 : 8;
  const padR = 12;
  const padT = 12;
  const padB = showAxis ? 26 : 8;
  const innerW = width - padL - padR;
  const innerH = height - padT - padB;

  const max = Math.max(...data, threshold ?? -Infinity);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const stepX = innerW / (data.length - 1);
  const yOf = (v: number) => padT + innerH - ((v - min) / range) * innerH;
  const xOf = (i: number) => padL + i * stepX;

  const points = data.map((v, i) => `${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`).join(" ");
  const gradientId = `line-${Math.random().toString(36).slice(2, 8)}`;

  const yTicks = 4;
  const ticks = Array.from({ length: yTicks + 1 }, (_, i) => min + (range * i) / yTicks);
  const xTickCount = 5;
  const xTicks = Array.from({ length: xTickCount }, (_, i) =>
    Math.round(((data.length - 1) * i) / (xTickCount - 1)),
  );

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {showAxis &&
        ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={padL}
              y1={yOf(t)}
              x2={width - padR}
              y2={yOf(t)}
              stroke="rgba(255,255,255,0.05)"
              strokeDasharray={i === 0 ? "0" : "3 4"}
            />
            <text
              x={padL - 6}
              y={yOf(t) + 3}
              textAnchor="end"
              fontSize="9"
              fontFamily="JetBrains Mono, monospace"
              fill="#5A5A62"
            >
              {t.toFixed(0)}
            </text>
          </g>
        ))}

      {showAxis &&
        xTicks.map((t, i) => (
          <text
            key={i}
            x={xOf(t)}
            y={height - 8}
            textAnchor="middle"
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
            fill="#5A5A62"
          >
            {t}
          </text>
        ))}

      {threshold !== undefined && (
        <g>
          <line
            x1={padL}
            y1={yOf(threshold)}
            x2={width - padR}
            y2={yOf(threshold)}
            stroke={thresholdColor}
            strokeDasharray="4 4"
            strokeWidth="1"
            opacity="0.7"
          />
          <text
            x={width - padR - 4}
            y={yOf(threshold) - 4}
            textAnchor="end"
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
            fill={thresholdColor}
          >
            threshold {threshold}
          </text>
        </g>
      )}

      <polygon
        points={`${padL},${padT + innerH} ${points} ${padL + innerW},${padT + innerH}`}
        fill={`url(#${gradientId})`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {yLabel && (
        <text
          x={10}
          y={padT + 4}
          fontSize="9"
          fontFamily="JetBrains Mono, monospace"
          fill="#8A8A92"
          letterSpacing="1"
        >
          {yLabel}
        </text>
      )}
    </svg>
  );
}
