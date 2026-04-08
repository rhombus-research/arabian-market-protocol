export type Scenario = 'forkbomb' | 'cryptojacking';

export interface SimulationConfig {
  scenario: Scenario;
  ticks: number;
  tick_delay_ms: number;
  fork_bomb_count: number;
  spawn_fee_ms: number;
  spawn_every: number;
  crypto_miner_count: number;
  critical_task_count: number;
  default_budget_ms: number;
  default_slice_ms: number;
  mint_rate_active_ms: number;
  mint_rate_throttled_ms: number;
  child_start_budget_ms: number;
}

export interface ProcessSnapshot {
  pid: number;
  name: string;
  process_state: string;
  execution_state?: string;
  budget?: number;
  spent?: number;
  last_bid?: number;
  cpu_share_pct: number;
}

export interface TransitionEvent {
  pid: number;
  from_state: string;
  to_state: string;
}

export interface MintEvent {
  pid: number;
  minted_ms: number;
  state: string;
}

export interface SchedulerTick {
  dispatch_pid: number | null;
  granted_ms: number;
  process_count: number;
  processes: ProcessSnapshot[];
}

export interface MarketSchedulerTick extends SchedulerTick {
  transitions: TransitionEvent[];
  mints: MintEvent[];
}

export interface SystemMetrics {
  rr_load_pct: number;
  market_load_pct: number;
  rr_throttled_count: number;
  market_throttled_count: number;
  market_bankrupt_count: number;
  critical_dispatch_ratio_rr: number;
  critical_dispatch_ratio_market: number;
}

export interface TickEvent {
  tick: number;
  scenario: string;
  rr: SchedulerTick;
  market: MarketSchedulerTick;
  system: SystemMetrics;
}

export interface SimulationStatus {
  session_id: string;
  status: string;
  tick: number;
  scenario: string;
}
