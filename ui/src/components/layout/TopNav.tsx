import { useSimulationStore } from '../../store/simulationStore';

export function TopNav() {
  const tick = useSimulationStore((s) => s.currentTick);
  const running = useSimulationStore((s) => s.running);

  return (
    <nav className="bg-gradient-to-r from-amp-panel via-amp-card to-amp-panel border-b border-amp-gold-dim/40 px-6 h-16 shrink-0">
      <div className="flex items-center justify-between h-full">
        <div className="flex items-center gap-3">
          <img src={`${import.meta.env.BASE_URL}lamp.png`} alt="AMP" className="h-9 w-auto object-contain" />
          <h1
            className="text-amp-gold"
            style={{ fontFamily: "'Instrument Serif', serif", fontSize: '32px', lineHeight: '1' }}
          >
            Arabian Market Protocol
          </h1>
        </div>

        <div className="flex items-center gap-6">
          {running && (
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amp-active animate-pulse" />
              <span className="text-sm text-amp-text-muted font-mono">Tick {tick}</span>
            </div>
          )}
          <div
            className="w-80 text-right text-amp-text-muted/40 pr-4"
            style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 200, fontSize: 'clamp(16pt, 2vw, 24pt)', letterSpacing: '-0.06em' }}
          >
            <span>rhombus </span>
            <span className="text-amp-rr-blue/40">research</span>
          </div>
        </div>
      </div>
    </nav>
  );
}
