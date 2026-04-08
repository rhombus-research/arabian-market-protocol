import { useSimulationStore } from '../../store/simulationStore';
import { CpuUsageChart } from '../charts/CpuUsageChart';
import { ProcessTable } from '../process/ProcessTable';

export function FairSchedulerPanel() {
  const processes = useSimulationStore((s) => s.rrProcesses);
  const system = useSimulationStore((s) => s.system);

  return (
    <div className="flex-1 bg-amp-panel border-r border-amp-gold-dim/20 flex flex-col min-h-0 min-w-0">
      {/* Header — same height as sidebar tabs */}
      <div className="px-4 flex items-center justify-between shrink-0 h-[41px] border-b border-amp-gold-dim/30 bg-amp-card/50">
        <h2 className="font-display text-2xl text-amp-rr-blue">Round Robin Scheduler</h2>
        <div className="flex items-center gap-3 text-xs text-amp-text-muted">
          <span>Load: <span className="text-amp-text font-mono">{system.rr_load_pct.toFixed(0)}%</span></span>
          <span>Critical: <span className="text-amp-text font-mono">{(system.critical_dispatch_ratio_rr * 100).toFixed(1)}%</span></span>
          <span>No Throttling</span>
        </div>
      </div>

      {/* Chart — fixed 60% */}
      <div className="h-[60%] shrink-0 p-3">
        <CpuUsageChart />
      </div>

      {/* Process table — fixed 40%, scrolls internally */}
      <div className="h-[40%] shrink-0 border-t border-amp-gold-dim/20 overflow-y-auto">
        <ProcessTable processes={processes} variant="rr" />
      </div>
    </div>
  );
}
