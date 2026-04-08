import { create } from 'zustand';
import type { Scenario, SimulationConfig } from '../types/simulation';

interface ConfigState {
  config: SimulationConfig;
  setScenario: (scenario: Scenario) => void;
  setParam: <K extends keyof SimulationConfig>(key: K, value: SimulationConfig[K]) => void;
  reset: () => void;
}

const defaults: SimulationConfig = {
  scenario: 'forkbomb',
  ticks: 0,
  tick_delay_ms: 100,
  fork_bomb_count: 60,
  spawn_fee_ms: 5,
  spawn_every: 1,
  crypto_miner_count: 1,
  critical_task_count: 1,
  default_budget_ms: 60,
  default_slice_ms: 10,
  mint_rate_active_ms: 2,
  mint_rate_throttled_ms: 1,
  child_start_budget_ms: 10,
};

export const useConfigStore = create<ConfigState>((set) => ({
  config: { ...defaults },
  setScenario: (scenario) =>
    set((s) => ({ config: { ...s.config, scenario } })),
  setParam: (key, value) =>
    set((s) => ({ config: { ...s.config, [key]: value } })),
  reset: () => set({ config: { ...defaults } }),
}));
