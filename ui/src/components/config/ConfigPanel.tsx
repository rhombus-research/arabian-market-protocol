import { useConfigStore } from '../../store/configStore';
import { useSimulationStore } from '../../store/simulationStore';
import { useSimulationWs } from '../../hooks/useSimulationWs';
import { ScenarioSelector } from './ScenarioSelector';
import { ParamSlider } from './ParamSlider';

export function ConfigPanel() {
  const { config, setScenario, setParam } = useConfigStore();
  const running = useSimulationStore((s) => s.running);
  const { connect, send, disconnect } = useSimulationWs();
  const clear = useSimulationStore((s) => s.clear);
  const setSession = useSimulationStore((s) => s.setSession);

  const isForkBomb = config.scenario === 'forkbomb';

  const handleStart = async () => {
    if (running) {
      send('stop');
      disconnect();
      return;
    }

    clear();

    const res = await fetch('/api/simulation/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    const data = await res.json();
    setSession(data.session_id);
    connect(data.session_id);
  };

  return (
    <div className="p-5 space-y-6">
      {/* Scenario selector */}
      <ScenarioSelector
        value={config.scenario}
        onChange={setScenario}
        disabled={running}
      />

      {/* Start / Stop button */}
      <button
        onClick={handleStart}
        className={`w-full py-2.5 rounded-lg font-semibold text-sm tracking-wide transition-all
          ${
            running
              ? 'bg-amp-bankrupt/90 text-white hover:bg-amp-bankrupt'
              : 'bg-gradient-to-r from-amp-gold to-amp-gold-bright text-amp-midnight hover:shadow-[0_0_20px_rgba(212,169,64,0.35)]'
          }`}
      >
        {running ? 'Stop Simulation' : 'Start Simulation'}
      </button>

      <Divider />

      {/* Simulation */}
      <Section label="Simulation">
        <ParamSlider
          label="Speed"
          unit="ms/tick"
          value={config.tick_delay_ms}
          min={50} max={500} step={10}
          onChange={(v) => {
            setParam('tick_delay_ms', v);
            if (running) send('speed', { tick_delay_ms: v });
          }}
        />
        <ParamSlider
          label="Max Ticks"
          value={config.ticks}
          min={0} max={2000} step={50}
          disabled={running}
          onChange={(v) => setParam('ticks', v)}
        />
      </Section>

      <Divider />

      {/* Process Setup */}
      <Section label="Process Setup" badge={running ? 'locked' : undefined}>
        <ParamSlider
          label="Critical Tasks"
          value={config.critical_task_count}
          min={1} max={3}
          disabled={running}
          onChange={(v) => setParam('critical_task_count', v)}
        />
        <ParamSlider
          label="Budget"
          unit="ms"
          value={config.default_budget_ms}
          min={20} max={120} step={10}
          disabled={running}
          onChange={(v) => setParam('default_budget_ms', v)}
        />
      </Section>

      <Divider />

      {/* Fork Bomb */}
      <div className={!isForkBomb ? 'opacity-30 pointer-events-none' : ''}>
        <Section label="Fork Bomb">
          <ParamSlider
            label="Max Processes"
            value={config.fork_bomb_count}
            min={10} max={60} step={5}
            disabled={running || !isForkBomb}
            onChange={(v) => setParam('fork_bomb_count', v)}
          />
          <ParamSlider
            label="Spawn Fee"
            unit="ms"
            value={config.spawn_fee_ms}
            min={1} max={15}
            disabled={!isForkBomb}
            onChange={(v) => {
              setParam('spawn_fee_ms', v);
              if (running) send('tune', { spawn_fee_ms: v });
            }}
          />
        </Section>
      </div>

      {/* Cryptojacking */}
      <div className={isForkBomb ? 'opacity-30 pointer-events-none' : ''}>
        <Section label="Cryptojacking">
          <ParamSlider
            label="Miners"
            value={config.crypto_miner_count}
            min={1} max={5}
            disabled={running || isForkBomb}
            onChange={(v) => setParam('crypto_miner_count', v)}
          />
        </Section>
      </div>

      <Divider />

      {/* Economic Tuning */}
      <Section label="Economic Tuning" badge="live">
        <ParamSlider
          label="Mint Rate (Throttled)"
          unit="ms/tick"
          value={config.mint_rate_throttled_ms}
          min={0} max={5}
          onChange={(v) => {
            setParam('mint_rate_throttled_ms', v);
            if (running) send('tune', { mint_rate_throttled_ms: v });
          }}
        />
      </Section>
    </div>
  );
}

function Section({ label, badge, children }: { label: string; badge?: 'locked' | 'live'; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs uppercase tracking-[0.15em] text-amp-text-muted/70 font-semibold">
          {label}
        </span>
        {badge === 'locked' && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-sm bg-amp-card text-amp-text-muted/50 border border-amp-gold-dim/15 uppercase tracking-wider">
            locked
          </span>
        )}
        {badge === 'live' && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-sm bg-amp-active/8 text-amp-active/80 border border-amp-active/15 uppercase tracking-wider">
            live
          </span>
        )}
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  );
}

function Divider() {
  return <div className="border-t border-amp-gold-dim/15" />;
}
