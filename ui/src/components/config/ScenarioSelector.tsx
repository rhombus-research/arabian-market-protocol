import type { Scenario } from '../../types/simulation';

interface ScenarioSelectorProps {
  value: Scenario;
  onChange: (scenario: Scenario) => void;
  disabled?: boolean;
}

const scenarios: { value: Scenario; label: string }[] = [
  { value: 'forkbomb', label: 'Fork Bomb' },
  { value: 'cryptojacking', label: 'Cryptojacking' },
];

export function ScenarioSelector({ value, onChange, disabled }: ScenarioSelectorProps) {
  return (
    <div className="flex w-full rounded-lg overflow-hidden border border-amp-gold-muted/50">
      {scenarios.map((s) => (
        <button
          key={s.value}
          disabled={disabled}
          onClick={() => onChange(s.value)}
          className={`flex-1 py-2 text-xs font-semibold tracking-wide uppercase transition-all
            ${
              value === s.value
                ? 'bg-amp-gold text-amp-midnight'
                : 'bg-amp-card text-amp-text-muted hover:bg-amp-card-hover hover:text-amp-text'
            }
            disabled:cursor-not-allowed disabled:opacity-50`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
