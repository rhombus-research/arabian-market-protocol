import type { ProcessSnapshot } from '../../types/simulation';
import { StatusBadge } from './StatusBadge';

interface ProcessTableProps {
  processes: ProcessSnapshot[];
  variant: 'rr' | 'market';
}

export function ProcessTable({ processes, variant }: ProcessTableProps) {
  // Show top processes, grouped: critical first, then benign, then attackers
  const sorted = [...processes].sort((a, b) => {
    const order = (name: string) => {
      if (name.startsWith('critical')) return 0;
      if (name === 'benign') return 1;
      return 2;
    };
    return order(a.name) - order(b.name) || a.pid - b.pid;
  });

  // Limit display
  const display = sorted.length > 12
    ? [...sorted.slice(0, 5), ...sorted.slice(-5)]
    : sorted;
  const truncated = sorted.length > 12;

  return (
    <div className="overflow-hidden border border-amp-gold-dim/20">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-amp-card text-amp-text-muted text-xs uppercase tracking-wider">
            <th className="py-1.5 px-3 text-left">Process</th>
            <th className="py-1.5 px-3 text-center">Status</th>
            <th className="py-1.5 px-3 text-right">
              {variant === 'rr' ? 'CPU Share' : 'Credits'}
            </th>
          </tr>
        </thead>
        <tbody>
          {display.length === 0 && (
            <tr>
              <td colSpan={3} className="py-3 px-3 text-center text-xs text-amp-text-muted/50">
                No simulation data
              </td>
            </tr>
          )}
          {display.map((p) => (
            <tr
              key={p.pid}
              className="border-t border-amp-gold-dim/10 hover:bg-amp-card-hover/50 transition-colors"
            >
              <td className="py-1 px-3 font-mono text-xs">{p.name}</td>
              <td className="py-1 px-3 text-center">
                <StatusBadge state={variant === 'market' ? (p.execution_state ?? p.process_state) : p.process_state} />
              </td>
              <td className="py-1 px-3 text-right font-mono text-xs">
                {variant === 'rr'
                  ? `${p.cpu_share_pct.toFixed(1)}%`
                  : `${p.budget ?? 0}`}
              </td>
            </tr>
          ))}
          {truncated && (
            <tr className="border-t border-amp-gold-dim/10">
              <td colSpan={3} className="py-1 px-3 text-center text-xs text-amp-text-muted">
                ... {sorted.length - 10} more processes ...
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
