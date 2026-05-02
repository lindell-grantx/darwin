import { useEffect, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { EvolutionEvent, FitnessCurveResponse } from '@contracts';

import { getFitnessCurve } from '../lib/api';
import { Spinner } from './Spinner';

interface Props {
  events: EvolutionEvent[];
}

export function FitnessCurve({ events }: Props) {
  const [data, setData] = useState<FitnessCurveResponse['series']>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getFitnessCurve()
      .then((r) => mounted && setData(r.series))
      .catch(() => mounted && setData([]))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  // Re-fetch curve when a generation.evolved event arrives.
  useEffect(() => {
    const last = events.at(-1);
    if (!last || last.event_type !== 'generation.evolved') return;
    getFitnessCurve()
      .then((r) => setData(r.series))
      .catch(() => undefined);
  }, [events]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner label="Loading fitness curve…" />
      </div>
    );
  }
  if (data.length === 0) {
    return <div className="text-xs text-rose-400">No fitness data yet.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
        <XAxis
          dataKey="generation"
          stroke="#71717a"
          fontSize={11}
          label={{ value: 'generation', position: 'insideBottom', offset: -2, fill: '#71717a', fontSize: 10 }}
        />
        <YAxis stroke="#71717a" fontSize={11} domain={[0, 1]} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #3f3f46',
            borderRadius: 6,
            fontSize: 12,
          }}
          labelStyle={{ color: '#a1a1aa' }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Line
          type="monotone"
          dataKey="best"
          stroke="#34d399"
          strokeWidth={2}
          dot={{ r: 3 }}
          isAnimationActive
        />
        <Line
          type="monotone"
          dataKey="mean"
          stroke="#fbbf24"
          strokeWidth={2}
          dot={{ r: 3 }}
          isAnimationActive
        />
        <Line
          type="monotone"
          dataKey="diversity"
          stroke="#60a5fa"
          strokeWidth={1.5}
          strokeDasharray="4 3"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
