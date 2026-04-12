import { create } from 'zustand';
import type {
  TickEvent,
  ProcessSnapshot,
  SystemMetrics,
} from '../types/simulation';
import { DEMO_SEED } from './demoSeed';

const MAX_HISTORY = 200;

export interface EventLogEntry {
  tick: number;
  type: 'dispatch' | 'transition' | 'mint';
  scheduler: 'rr' | 'market';
  detail: string;
}

interface SimulationState {
  sessionId: string | null;
  running: boolean;
  paused: boolean;
  currentTick: number;
  tickHistory: TickEvent[];
  rrProcesses: ProcessSnapshot[];
  marketProcesses: ProcessSnapshot[];
  system: SystemMetrics;
  eventLog: EventLogEntry[];

  setSession: (id: string | null) => void;
  setRunning: (running: boolean) => void;
  setPaused: (paused: boolean) => void;
  pushTick: (event: TickEvent) => void;
  clear: () => void;
}

const emptyMetrics: SystemMetrics = {
  rr_load_pct: 0,
  market_load_pct: 0,
  rr_throttled_count: 0,
  market_throttled_count: 0,
  market_bankrupt_count: 0,
  critical_dispatch_ratio_rr: 0,
  critical_dispatch_ratio_market: 0,
};

// Check if backend is available — if not, seed with demo data
const isStatic = typeof window !== 'undefined' &&
  !window.location.port &&
  window.location.hostname.includes('github.io');

const initialState = isStatic
  ? {
      currentTick: DEMO_SEED.currentTick,
      tickHistory: DEMO_SEED.tickHistory,
      rrProcesses: DEMO_SEED.rrProcesses,
      marketProcesses: DEMO_SEED.marketProcesses,
      system: DEMO_SEED.system,
      eventLog: [
        { tick: 0, type: 'transition' as const, scheduler: 'market' as const, detail: 'Demo mode — backend not connected' },
      ],
    }
  : {
      currentTick: 0,
      tickHistory: [],
      rrProcesses: [],
      marketProcesses: [],
      system: { ...emptyMetrics },
      eventLog: [],
    };

export const useSimulationStore = create<SimulationState>((set) => ({
  sessionId: null,
  running: false,
  paused: false,
  ...initialState,

  setSession: (id) => set({ sessionId: id }),
  setRunning: (running) => set({ running }),
  setPaused: (paused) => set({ paused }),

  pushTick: (event) =>
    set((state) => {
      const history = [...state.tickHistory, event];
      if (history.length > MAX_HISTORY) history.shift();

      // Build event log entries for this tick
      const newEntries: EventLogEntry[] = [];

      if (event.rr.dispatch_pid !== null) {
        const proc = event.rr.processes.find(
          (p) => p.pid === event.rr.dispatch_pid
        );
        newEntries.push({
          tick: event.tick,
          type: 'dispatch',
          scheduler: 'rr',
          detail: `${proc?.name ?? `pid ${event.rr.dispatch_pid}`} granted ${event.rr.granted_ms}ms`,
        });
      }

      if (event.market.dispatch_pid !== null) {
        const proc = event.market.processes.find(
          (p) => p.pid === event.market.dispatch_pid
        );
        newEntries.push({
          tick: event.tick,
          type: 'dispatch',
          scheduler: 'market',
          detail: `${proc?.name ?? `pid ${event.market.dispatch_pid}`} granted ${event.market.granted_ms}ms`,
        });
      }

      for (const t of event.market.transitions) {
        newEntries.push({
          tick: event.tick,
          type: 'transition',
          scheduler: 'market',
          detail: `pid ${t.pid}: ${t.from_state} -> ${t.to_state}`,
        });
      }

      for (const m of event.market.mints) {
        newEntries.push({
          tick: event.tick,
          type: 'mint',
          scheduler: 'market',
          detail: `pid ${m.pid} +${m.minted_ms}ms (${m.state})`,
        });
      }

      const log = [...state.eventLog, ...newEntries];
      if (log.length > 500) log.splice(0, log.length - 500);

      return {
        currentTick: event.tick,
        tickHistory: history,
        rrProcesses: event.rr.processes,
        marketProcesses: event.market.processes,
        system: event.system,
        eventLog: log,
      };
    }),

  clear: () =>
    set({
      sessionId: null,
      running: false,
      paused: false,
      currentTick: 0,
      tickHistory: [],
      rrProcesses: [],
      marketProcesses: [],
      system: { ...emptyMetrics },
      eventLog: [],
    }),
}));
