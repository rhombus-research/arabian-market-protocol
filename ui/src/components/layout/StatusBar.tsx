import { useSimulationStore } from '../../store/simulationStore';
import { useConfigStore } from '../../store/configStore';

export function StatusBar() {
  const system = useSimulationStore((s) => s.system);
  const scenario = useConfigStore((s) => s.config.scenario);
  const running = useSimulationStore((s) => s.running);
  const tick = useSimulationStore((s) => s.currentTick);

  return (
    <div className="bg-amp-panel border-t border-amp-gold-dim/30 px-6 h-8 shrink-0 flex items-center gap-6 text-xs">
      {running ? (
        <>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amp-active" />
            <span className="text-amp-text-muted">RR Load</span>
            <span className="font-mono text-amp-text">{system.rr_load_pct.toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amp-gold" />
            <span className="text-amp-text-muted">Market Load</span>
            <span className="font-mono text-amp-text">{system.market_load_pct.toFixed(0)}%</span>
          </div>

          <div className="ml-auto flex items-center gap-4">
            {scenario === 'forkbomb' && system.market_bankrupt_count > 0 && (
              <span className="text-amp-bankrupt font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amp-bankrupt animate-pulse" />
                Fork Bomb Bankrupt!
              </span>
            )}
            {scenario === 'cryptojacking' && system.market_throttled_count > 0 && (
              <span className="text-amp-throttled font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amp-throttled animate-pulse" />
                Attacker Throttled
              </span>
            )}
            <span className="text-amp-active font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amp-active" />
              Critical Tasks Protected
            </span>
          </div>
        </>
      ) : (
        <span className="text-amp-text-muted/50">
          {tick > 0 ? `Simulation ended at tick ${tick}` : 'Ready'}
        </span>
      )}
    </div>
  );
}
