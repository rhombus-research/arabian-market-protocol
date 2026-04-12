import type { TickEvent } from '../types/simulation';

/**
 * Pre-built simulation snapshots for static GitHub Pages demo.
 * Shows a fork bomb scenario ~80 ticks in where:
 * - RR has 60 processes (flooded)
 * - Market has 14 processes, attacker bankrupt, critical protected
 */

function buildDemoHistory(): TickEvent[] {
  const ticks: TickEvent[] = [];

  for (let t = 0; t <= 80; t++) {
    // RR: process count climbs to 60 by tick ~20, stays there
    const rrProcs = Math.min(60, 3 + t * 3);
    // Market: climbs to ~14 by tick ~4, then stops (attacker bankrupts)
    const marketProcs = Math.min(14, 3 + t * 3);

    // Attacker budget: drops fast, hits 0 by tick ~12
    const attackerBudget = Math.max(0, 60 - t * 5);

    ticks.push({
      tick: t,
      scenario: 'forkbomb',
      rr: {
        dispatch_pid: t % 3 === 0 ? 1 : (t % 2 === 0 ? 2 : 3 + (t % rrProcs)),
        granted_ms: 10,
        process_count: rrProcs,
        processes: [],
      },
      market: {
        dispatch_pid: t % 2 === 0 ? 1 : 2,
        granted_ms: 10,
        process_count: marketProcs,
        processes: [],
        transitions: [],
        mints: [],
      },
      system: {
        rr_load_pct: 100,
        market_load_pct: 100,
        rr_throttled_count: 0,
        market_throttled_count: attackerBudget > 0 ? 0 : Math.min(12, marketProcs - 2),
        market_bankrupt_count: attackerBudget <= 0 ? 1 : 0,
        critical_dispatch_ratio_rr: 1 / rrProcs,
        critical_dispatch_ratio_market: 0.35,
      },
    });
  }

  return ticks;
}

// Final-state process snapshots
const rrProcesses = [
  { pid: 1, name: 'critical-burst', process_state: 'RUNNABLE', cpu_share_pct: 1.7 },
  { pid: 2, name: 'benign', process_state: 'RUNNABLE', cpu_share_pct: 1.7 },
  { pid: 3, name: 'attacker-root', process_state: 'RUNNABLE', cpu_share_pct: 1.7 },
  ...Array.from({ length: 10 }, (_, i) => ({
    pid: 4 + i,
    name: `attacker-${4 + i}`,
    process_state: 'RUNNABLE',
    cpu_share_pct: 1.7,
  })),
];

const marketProcesses = [
  { pid: 1, name: 'critical-burst', process_state: 'RUNNABLE', execution_state: 'ACTIVE', budget: 58, spent: 120, last_bid: 10, cpu_share_pct: 0 },
  { pid: 2, name: 'benign', process_state: 'RUNNABLE', execution_state: 'ACTIVE', budget: 245, spent: 36, last_bid: 3, cpu_share_pct: 0 },
  { pid: 3, name: 'attacker-root', process_state: 'RUNNABLE', execution_state: 'BANKRUPT', budget: 0, spent: 60, last_bid: 0, cpu_share_pct: 0 },
  ...Array.from({ length: 11 }, (_, i) => ({
    pid: 4 + i,
    name: `attacker-${4 + i}`,
    process_state: 'RUNNABLE',
    execution_state: 'THROTTLED' as const,
    budget: 3 + Math.floor(Math.random() * 5),
    spent: 10,
    last_bid: 2,
    cpu_share_pct: 0,
  })),
];

export const DEMO_SEED = {
  tickHistory: buildDemoHistory(),
  rrProcesses,
  marketProcesses,
  currentTick: 80,
  system: {
    rr_load_pct: 100,
    market_load_pct: 100,
    rr_throttled_count: 0,
    market_throttled_count: 11,
    market_bankrupt_count: 1,
    critical_dispatch_ratio_rr: 0.017,
    critical_dispatch_ratio_market: 0.35,
  },
};
