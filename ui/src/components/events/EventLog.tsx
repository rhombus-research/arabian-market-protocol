import { useState, useRef, useEffect } from 'react';
import { useSimulationStore } from '../../store/simulationStore';

const typeColors: Record<string, string> = {
  dispatch: 'text-amp-text',
  transition: 'text-amp-gold',
  mint: 'text-amp-active',
};

const typeBg: Record<string, string> = {
  dispatch: 'bg-amp-text/10',
  transition: 'bg-amp-gold/10',
  mint: 'bg-amp-active/10',
};

export function EventLog() {
  const [filter, setFilter] = useState<string>('all');
  const eventLog = useSimulationStore((s) => s.eventLog);
  const scrollRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);

  const filtered = filter === 'all'
    ? eventLog
    : eventLog.filter((e) => e.type === filter);

  const display = filtered.slice(-200);

  // Auto-scroll only if user is already at the bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (el && shouldAutoScroll.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [display.length]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    shouldAutoScroll.current = atBottom;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="px-2 py-2 border-b border-amp-gold-dim/20 flex items-center gap-1 shrink-0">
        {['all', 'dispatch', 'transition', 'mint'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`flex-1 py-1 text-xs rounded transition-colors capitalize ${
              filter === f
                ? 'bg-amp-gold text-amp-midnight font-semibold'
                : 'text-amp-text-muted hover:text-amp-text hover:bg-amp-card-hover/50'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Scrollable log area */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5 font-mono text-sm min-h-0"
      >
        {display.length === 0 && (
          <div className="flex items-center justify-center h-full text-amp-text-muted text-xs">
            Start a simulation to see events
          </div>
        )}
        {display.map((entry, i) => (
          <div key={i} className={`py-1 px-2 rounded ${typeBg[entry.type]}`}>
            <div className="flex items-center gap-1.5">
              <span className="text-amp-text-muted">t={entry.tick}</span>
              <span className={`uppercase text-xs font-bold px-1 py-px rounded ${typeColors[entry.type]} ${typeBg[entry.type]}`}>
                {entry.type}
              </span>
              <span className="text-xs text-amp-gold-muted">{entry.scheduler}</span>
            </div>
            <div className="text-amp-text mt-0.5 leading-snug">{entry.detail}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
