interface ParamSliderProps {
  label: string;
  unit?: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}

export function ParamSlider({ label, unit, value, min, max, step = 1, disabled, onChange }: ParamSliderProps) {
  return (
    <div className={`group ${disabled ? 'opacity-35' : ''}`}>
      <div className="flex items-baseline justify-between mb-1.5">
        <label className="text-xs text-amp-text-muted tracking-wide">{label}</label>
        <div className="text-xs font-mono">
          <span className="text-amp-gold">{value}</span>
          {unit && <span className="text-amp-text-muted/60 ml-1">{unit}</span>}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1 rounded-full appearance-none cursor-pointer
          bg-amp-gold-dim/60
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:w-3
          [&::-webkit-slider-thumb]:h-3
          [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:bg-amp-gold
          [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(212,169,64,0.4)]
          [&::-webkit-slider-thumb]:cursor-pointer
          [&::-webkit-slider-thumb]:transition-shadow
          group-hover:[&::-webkit-slider-thumb]:shadow-[0_0_12px_rgba(212,169,64,0.6)]
          disabled:cursor-not-allowed"
      />
    </div>
  );
}
