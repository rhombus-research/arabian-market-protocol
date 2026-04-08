interface StatusBadgeProps {
  state: string;
}

const stateStyles: Record<string, string> = {
  ACTIVE: 'bg-amp-active/20 text-amp-active border-amp-active/40',
  RUNNING: 'bg-amp-active/20 text-amp-active border-amp-active/40',
  RUNNABLE: 'bg-amp-active/20 text-amp-active border-amp-active/40',
  THROTTLED: 'bg-amp-throttled/20 text-amp-throttled border-amp-throttled/40',
  BANKRUPT: 'bg-amp-bankrupt/20 text-amp-bankrupt border-amp-bankrupt/40 animate-[pulse-glow_2s_ease-in-out_infinite]',
};

export function StatusBadge({ state }: StatusBadgeProps) {
  const style = stateStyles[state] ?? 'bg-amp-text-muted/20 text-amp-text-muted border-amp-text-muted/40';

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full border ${style}`}
    >
      {state}
    </span>
  );
}
