import { TopNav } from './components/layout/TopNav';
import { StatusBar } from './components/layout/StatusBar';
import { Sidebar } from './components/layout/Sidebar';
import { FairSchedulerPanel } from './components/panels/FairSchedulerPanel';
import { MarketSchedulerPanel } from './components/panels/MarketSchedulerPanel';

export default function App() {
  return (
    <div className="h-screen flex flex-col bg-amp-midnight overflow-hidden">
      <TopNav />

      <div className="flex-1 flex min-h-0">
        {/* Main simulation area — two columns side by side, no outer padding */}
        <main className="flex-1 flex min-w-0 min-h-0">
          <FairSchedulerPanel />
          <MarketSchedulerPanel />
        </main>

        {/* Right sidebar: Controls / Log tabs */}
        <Sidebar />
      </div>

      <StatusBar />
    </div>
  );
}
