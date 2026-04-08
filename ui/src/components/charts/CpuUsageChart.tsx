import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useSimulationStore } from '../../store/simulationStore';
import { useConfigStore } from '../../store/configStore';

const placeholder = [{ tick: 0, procs: 0 }];

export function CpuUsageChart() {
  const tickHistory = useSimulationStore((s) => s.tickHistory);
  const config = useConfigStore((s) => s.config);

  // Use fork_bomb_count as the Y ceiling since that's the max procs RR will hit
  const yMax = config.scenario === 'forkbomb' ? config.fork_bomb_count : 10;

  const data = tickHistory.length > 0
    ? tickHistory.map((t) => ({
        tick: t.tick,
        procs: t.rr.process_count,
      }))
    : placeholder;

  return (
    <div className="relative w-full h-full">
      <div className="absolute inset-0">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#5a482040" />
          <XAxis
            dataKey="tick"
            tick={{ fill: '#a09880', fontSize: 12 }}
            stroke="#5a4820"
          />
          <YAxis
            tick={{ fill: '#a09880', fontSize: 12 }}
            stroke="#5a4820"
            domain={[0, yMax]}
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
          <Line
            type="monotone"
            dataKey="procs"
            name="Processes"
            stroke="#6880a0"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}
