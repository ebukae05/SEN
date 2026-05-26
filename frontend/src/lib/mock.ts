import type { FleetEngine, Severity } from "./types";

function seededRandom(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 2 ** 32;
    return state / 2 ** 32;
  };
}

function severityFromRul(rul: number, threshold: number): Severity {
  if (rul < threshold * 0.6) return "critical";
  if (rul < threshold * 1.3) return "warning";
  return "healthy";
}

export function makeMockFleet(count = 100): FleetEngine[] {
  const rand = seededRandom(7);
  const threshold = 30;
  const engines: FleetEngine[] = [];
  for (let i = 1; i <= count; i++) {
    const roll = rand();
    let rul: number;
    if (roll < 0.12) rul = Math.round(4 + rand() * 14);
    else if (roll < 0.32) rul = Math.round(20 + rand() * 18);
    else rul = Math.round(45 + rand() * 95);

    const points = 24;
    const startRul = rul + 18 + rand() * 12;
    const trend = Array.from({ length: points }, (_, k) => {
      const progress = k / (points - 1);
      const base = startRul - (startRul - rul) * progress;
      const noise = (rand() - 0.5) * 1.6;
      return Math.max(0, base + noise);
    });

    const degradation_rate = -(0.3 + rand() * 1.5);
    engines.push({
      engine_id: i,
      predicted_rul: rul,
      severity: severityFromRul(rul, threshold),
      alert: rul < threshold,
      threshold,
      trend,
      degradation_rate,
      last_cycle: 120 + Math.round(rand() * 80),
    });
  }
  return engines.sort((a, b) => a.predicted_rul - b.predicted_rul);
}
