interface Props {
  raw: number[];
  regression: { slope: number; intercept: number };
  fleet: number[];
  height?: number;
}

export function SensorChart({ raw, regression, fleet, height = 280 }: Props) {
  const width = 800;
  const padL = 44;
  const padR = 16;
  const padT = 16;
  const padB = 30;
  const innerW = width - padL - padR;
  const innerH = height - padT - padB;
  const n = raw.length;
  if (n === 0) return null;

  const allValues = [
    ...raw,
    ...fleet,
    regression.intercept,
    regression.intercept + regression.slope * (n - 1),
  ];
  const dataMax = Math.max(...allValues);
  const dataMin = Math.min(...allValues);
  const pad = (dataMax - dataMin) * 0.08 || 0.05;
  const max = dataMax + pad;
  const min = dataMin - pad;
  const range = max - min || 1;

  const xOf = (i: number) => padL + (i / (n - 1)) * innerW;
  const yOf = (v: number) =>
    padT + innerH - ((v - min) / range) * innerH;

  const path = (series: number[]) =>
    series.map((v, i) => `${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`).join(" ");

  const regSeries = Array.from(
    { length: n },
    (_, i) => regression.intercept + regression.slope * i,
  );

  const yTickCount = 4;
  const yTicks = Array.from({ length: yTickCount + 1 }, (_, i) =>
    min + (range * i) / yTickCount,
  );
  const xTickCount = 6;
  const xTicks = Array.from({ length: xTickCount }, (_, i) =>
    Math.round(((n - 1) * i) / (xTickCount - 1)),
  );

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="raw-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#C084FC" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#C084FC" stopOpacity="0" />
        </linearGradient>
      </defs>

      {yTicks.map((t, i) => (
        <g key={`y${i}`}>
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
            {t.toFixed(2)}
          </text>
        </g>
      ))}

      {xTicks.map((t) => (
        <text
          key={`x${t}`}
          x={xOf(t)}
          y={height - 10}
          textAnchor="middle"
          fontSize="9"
          fontFamily="JetBrains Mono, monospace"
          fill="#5A5A62"
        >
          {t}
        </text>
      ))}

      <polygon
        points={`${padL},${padT + innerH} ${path(raw)} ${padL + innerW},${padT + innerH}`}
        fill="url(#raw-fill)"
      />

      <polyline
        points={path(fleet)}
        fill="none"
        stroke="#8A8A92"
        strokeWidth="1.25"
        strokeDasharray="4 4"
        opacity="0.85"
      />

      <polyline
        points={path(regSeries)}
        fill="none"
        stroke="#F59E0B"
        strokeWidth="1.5"
        strokeDasharray="6 3"
        opacity="0.95"
      />

      <polyline
        points={path(raw)}
        fill="none"
        stroke="#C084FC"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      <g transform={`translate(${padL + 8}, ${padT + 8})`}>
        <LegendDot color="#C084FC" label="Raw signal" />
        <g transform="translate(110, 0)">
          <LegendDot color="#F59E0B" label="Linear regression" dashed />
        </g>
        <g transform="translate(260, 0)">
          <LegendDot color="#8A8A92" label="Fleet average" dashed />
        </g>
      </g>
    </svg>
  );
}

function LegendDot({
  color,
  label,
  dashed,
}: {
  color: string;
  label: string;
  dashed?: boolean;
}) {
  return (
    <g>
      <line
        x1={0}
        y1={4}
        x2={18}
        y2={4}
        stroke={color}
        strokeWidth="1.75"
        strokeDasharray={dashed ? "4 3" : "0"}
      />
      <text
        x={24}
        y={7}
        fontSize="10"
        fontFamily="Inter, sans-serif"
        fill="#8A8A92"
      >
        {label}
      </text>
    </g>
  );
}
