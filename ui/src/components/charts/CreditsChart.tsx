import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useSimulationStore } from '../../store/simulationStore';
import { useConfigStore } from '../../store/configStore';

const placeholder = [{ tick: 0, criticalBudget: 0, attackerBudget: 0, procs: 0 }];

export function CreditsChart() {
  const tickHistory = useSimulationStore((s) => s.tickHistory);
  const config = useConfigStore((s) => s.config);

  const budgetMax = config.default_budget_ms;
  const procsMax = config.scenario === 'forkbomb' ? config.fork_bomb_count : 10;

  const data = tickHistory.length > 0
    ? tickHistory.map((t) => {
        const critical = t.market.processes.find((p) => p.name.startsWith('critical'));
        const attacker = t.market.processes.find(
          (p) => p.name.startsWith('attacker') || p.name.startsWith('cryptojack')
        );
        return {
          tick: t.tick,
          criticalBudget: critical?.budget ?? 0,
          attackerBudget: attacker?.budget ?? 0,
          procs: t.market.process_count,
        };
      })
    : placeholder;

  return (
    <div className="relative w-full h-full">
      <div className="absolute inset-0">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#5a482040" />
          <XAxis
            dataKey="tick"
            tick={{ fill: '#a09880', fontSize: 12 }}
            stroke="#5a4820"
          />
          <YAxis
            yAxisId="budget"
            tick={{ fill: '#a09880', fontSize: 12 }}
            stroke="#5a4820"
            domain={[0, budgetMax]}
          />
          <YAxis
            yAxisId="procs"
            orientation="right"
            tick={{ fill: '#a09880', fontSize: 12 }}
            stroke="#5a4820"
            domain={[0, procsMax]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#12121f',
              border: '1px solid #8a7030',
              borderRadius: 8,
              color: '#e8e0d0',
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, color: '#a09880' }}
          />
          <Bar
            yAxisId="budget"
            dataKey="criticalBudget"
            name="Critical Budget"
            fill="#40c080"
            opacity={0.7}
            isAnimationActive={false}
          />
          <Bar
            yAxisId="budget"
            dataKey="attackerBudget"
            name="Attacker Budget"
            fill="#c04040"
            opacity={0.7}
            isAnimationActive={false}
          />
          <Line
            yAxisId="procs"
            type="monotone"
            dataKey="procs"
            name="Processes"
            stroke="#d4a940"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}
