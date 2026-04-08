import { useState } from 'react';
import { ConfigPanel } from '../config/ConfigPanel';
import { EventLog } from '../events/EventLog';
import { useSimulationStore } from '../../store/simulationStore';

type Tab = 'controls' | 'log';

export function Sidebar() {
  const [activeTab, setActiveTab] = useState<Tab>('controls');
  const eventCount = useSimulationStore((s) => s.eventLog.length);

  return (
    <aside className="w-80 shrink-0 bg-amp-panel flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex border-b border-amp-gold-dim/30 shrink-0 h-[41px]">
        <TabButton
          label="Controls"
          active={activeTab === 'controls'}
          onClick={() => setActiveTab('controls')}
        />
        <TabButton
          label={`Ledger (${eventCount})`}
          active={activeTab === 'log'}
          onClick={() => setActiveTab('log')}
        />
      </div>

      {/* Tab content - fills remaining space, scrolls internally */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {activeTab === 'controls' ? <ConfigPanel /> : <EventLog />}
      </div>
    </aside>
  );
}

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 px-4 py-2.5 text-sm font-medium transition-all
        ${active
          ? 'text-amp-gold border-b-2 border-amp-gold bg-amp-card/50'
          : 'text-amp-text-muted hover:text-amp-text hover:bg-amp-card-hover/30'
        }`}
    >
      {label}
    </button>
  );
}
