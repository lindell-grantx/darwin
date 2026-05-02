import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
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

  useEffect(() => {
    const last = events.at(-1);
    if (!last || last.event_type !== 'generation.evolved') return;
    getFitnessCurve()
      .then((r) => setData(r.series))
      .catch(() => undefined);
  }, [events]);

  const latest = data.at(-1);
  const earliest = data.at(0);
  const delta = useMemo(() => {
    if (!latest || !earliest || data.length < 2) return null;
    return latest.best - earliest.best;
  }, [data, latest, earliest]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner label="reading the records…" />
      </div>
    );
  }
  if (data.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center">
        <span className="font-display text-base italic text-bone-fade">
          no generations recorded
        </span>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-2 px-3 pt-2 pb-2">
      {/* Live readouts */}
      <div className="flex items-baseline gap-4 border-b border-rule pb-2">
        <Readout
          label="Best"
          value={latest?.best != null ? latest.best.toFixed(3) : '—'}
          color="moss"
        />
        <Readout
          label="Mean"
          value={latest?.mean != null ? latest.mean.toFixed(3) : '—'}
          color="brass"
        />
        <Readout
          label="Diversity"
          value={latest?.diversity != null ? latest.diversity.toFixed(3) : '—'}
          color="bone-dim"
        />
        <div className="ml-auto flex items-baseline gap-1.5">
          <span className="label-cap">Δ since gen 0</span>
          <span
            className={`numeric font-mono text-sm ${
              delta == null ? 'text-bone-fade' : delta >= 0 ? 'text-moss' : 'text-oxblood'
            }`}
          >
            {delta == null ? '—' : `${delta >= 0 ? '+' : ''}${delta.toFixed(3)}`}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 18, bottom: 18, left: -8 }}>
            <defs>
              <linearGradient id="bestArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8eb190" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#8eb190" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="var(--color-rule)"
              strokeDasharray="2 4"
              vertical={false}
            />
            <XAxis
              dataKey="generation"
              tickLine={false}
              axisLine={{ stroke: 'var(--color-rule-strong)' }}
              padding={{ left: 6, right: 6 }}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              tickLine={false}
              axisLine={{ stroke: 'var(--color-rule-strong)' }}
              tickFormatter={(v: number) => v.toFixed(2)}
            />
            <Tooltip content={<JournalTooltip />} cursor={{ stroke: 'var(--color-brass)', strokeDasharray: '2 3' }} />
            <Area
              type="monotone"
              dataKey="best"
              fill="url(#bestArea)"
              stroke="none"
              isAnimationActive
            />
            <Line
              type="monotone"
              dataKey="best"
              name="best"
              stroke="#8eb190"
              strokeWidth={2}
              dot={{ r: 2.5, fill: '#8eb190', stroke: 'var(--color-ink-0)', strokeWidth: 1 }}
              activeDot={{ r: 4, fill: '#d4a44a', stroke: 'var(--color-ink-0)', strokeWidth: 2 }}
              isAnimationActive
            />
            <Line
              type="monotone"
              dataKey="mean"
              name="mean"
              stroke="#d4a44a"
              strokeWidth={1.5}
              dot={{ r: 2, fill: '#d4a44a', stroke: 'var(--color-ink-0)', strokeWidth: 1 }}
              isAnimationActive
            />
            <Line
              type="monotone"
              dataKey="diversity"
              name="diversity"
              stroke="#a89c80"
              strokeWidth={1}
              strokeDasharray="3 3"
              dot={false}
              isAnimationActive
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Caption */}
      <div className="flex items-center justify-between gap-3 border-t border-rule pt-1.5">
        <span className="font-display text-[11px] italic text-bone-fade">
          Fig. ii — selective fitness across {data.length} generations
        </span>
        <Legend />
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */

function Readout({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: 'moss' | 'brass' | 'bone-dim';
}) {
  const cls =
    color === 'moss' ? 'text-moss' : color === 'brass' ? 'text-brass-bright' : 'text-bone-dim';
  return (
    <div className="flex flex-col">
      <span className="label-cap">{label}</span>
      <span className={`numeric font-mono text-base font-semibold ${cls}`}>{value}</span>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.18em] text-bone-fade">
      <LegendDot color="#8eb190" label="best" />
      <LegendDot color="#d4a44a" label="mean" />
      <LegendDot color="#a89c80" label="div." dashed />
    </div>
  );
}
function LegendDot({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className="inline-block h-[2px] w-4"
        style={{
          background: dashed
            ? `repeating-linear-gradient(90deg, ${color} 0 3px, transparent 3px 6px)`
            : color,
        }}
      />
      <span>{label}</span>
    </span>
  );
}

interface TooltipPayloadItem {
  dataKey?: string | number;
  value?: number;
}
interface JournalTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
}

function JournalTooltip({ active, payload, label }: JournalTooltipProps) {
  if (!active || !payload?.length) return null;
  const fmt = (k: string) =>
    payload.find((p) => p.dataKey === k)?.value as number | undefined;
  return (
    <div className="border border-brass-dim bg-ink-1 px-2.5 py-1.5 font-mono text-[11px] shadow-[0_8px_20px_-10px_rgba(0,0,0,0.7)]">
      <div className="mb-1 label-cap text-brass-bright">Gen {label}</div>
      <Row label="best" v={fmt('best')} color="text-moss" />
      <Row label="mean" v={fmt('mean')} color="text-brass-bright" />
      <Row label="div." v={fmt('diversity')} color="text-bone-dim" />
    </div>
  );
}
function Row({ label, v, color }: { label: string; v: number | undefined; color: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-bone-fade">{label}</span>
      <span className={`numeric ${color}`}>{v == null ? '—' : v.toFixed(3)}</span>
    </div>
  );
}
