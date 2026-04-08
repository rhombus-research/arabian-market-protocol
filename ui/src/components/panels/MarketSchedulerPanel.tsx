import { useSimulationStore } from '../../store/simulationStore';
import { CreditsChart } from '../charts/CreditsChart';
import { ProcessTable } from '../process/ProcessTable';

export function MarketSchedulerPanel() {
  const processes = useSimulationStore((s) => s.marketProcesses);
  const system = useSimulationStore((s) => s.system);

  return (
    <div className="flex-1 bg-amp-panel border-r border-amp-gold-dim/20 flex flex-col min-h-0 min-w-0">
      {/* Header — same height as sidebar tabs */}
      <div className="px-4 flex items-center justify-between shrink-0 h-[41px] border-b border-amp-gold-dim/30" style={{ background: 'linear-gradient(to right, rgba(220,36,36,0.15), rgba(74,86,157,0.15))' }}>
        <h2 className="font-display text-2xl text-amp-gold">Arabian Market</h2>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-amp-text-muted">Load: <span className="text-amp-text font-mono">{system.market_load_pct.toFixed(0)}%</span></span>
          <span className="text-amp-text-muted">Critical: <span className="text-amp-gold font-mono font-semibold">{(system.critical_dispatch_ratio_market * 100).toFixed(1)}%</span></span>
          {system.market_bankrupt_count > 0 && (
            <span className="text-amp-bankrupt font-semibold">{system.market_bankrupt_count} Bankrupt</span>
          )}
          {system.market_throttled_count > 0 && (
            <span className="text-amp-throttled font-semibold">{system.market_throttled_count} Throttled</span>
          )}
        </div>
      </div>

      {/* Chart — fixed 60% */}
      <div className="h-[60%] shrink-0 p-3">
        <CreditsChart />
      </div>

      {/* Process table — fixed 40%, scrolls internally */}
      <div className="h-[40%] shrink-0 border-t border-amp-gold-dim/20 overflow-y-auto">
        <ProcessTable processes={processes} variant="market" />
      </div>
    </div>
  );
}
