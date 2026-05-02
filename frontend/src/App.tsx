import { useEffect, useState, type ReactNode } from 'react';

import type { EvolutionEvent } from '@contracts';

import { EventTicker } from './components/EventTicker';
import { FamilyTree } from './components/FamilyTree';
import { FitnessCurve } from './components/FitnessCurve';
import { LiveQuery } from './components/LiveQuery';
import { useEvolutionEvents } from './lib/sse';

export function App() {
  const events = useEvolutionEvents();
  const lastGen = [...events].reverse().find((e) => e.event_type === 'generation.evolved');
  const currentGen = lastGen?.generation ?? 0;
  const champCount = events.filter((e) => e.event_type === 'champion.promoted').length;

  return (
    <div className="relative flex h-screen flex-col overflow-hidden text-bone">
      <Masthead currentGen={currentGen} events={events} champCount={champCount} />

      <main className="relative grid min-h-0 flex-1 grid-cols-12 grid-rows-2 gap-3 px-5 pb-5">
        <Plate
          number="I"
          title="Phylogeny"
          caption="Population & lineal descent"
          className="col-span-7 row-span-2"
          delay={0}
        >
          <FamilyTree />
        </Plate>

        <Plate
          number="II"
          title="Selective Fitness"
          caption="Generational metrics over time"
          className="col-span-5"
          delay={0.18}
        >
          <FitnessCurve events={events} />
        </Plate>

        <Plate
          number="III"
          title="Field Inquiry"
          caption="Question the evolved population"
          className="col-span-5"
          delay={0.36}
        >
          <LiveQuery />
        </Plate>
      </main>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */

interface MastheadProps {
  currentGen: number;
  champCount: number;
  events: EvolutionEvent[];
}

function Masthead({ currentGen, champCount, events }: MastheadProps) {
  const date = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <header className="relative z-10 shrink-0 px-5 pt-5">
      <div className="flex items-end justify-between gap-8">
        {/* Wordmark */}
        <div className="flex items-end gap-5">
          <h1 className="font-display animate-mast text-[68px] italic leading-[0.82] tracking-[-0.02em] text-bone">
            Darwin
          </h1>
          <div className="flex flex-col gap-0.5 pb-1.5">
            <span className="label-cap">Vol. I · No. 12 · MMXXVI</span>
            <span className="font-display text-[18px] italic leading-tight text-bone-dim">
              An evolutionary retrieval journal
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-bone-fade">
              {date}
            </span>
          </div>
        </div>

        {/* Stats ledger */}
        <div className="flex items-stretch gap-px">
          <Stat label="Generation" value={String(currentGen).padStart(3, '0')} accent="brass" />
          <Stat label="Champions" value={String(champCount).padStart(2, '0')} accent="brass" />
          <Stat label="Wire" value="LIVE" accent="moss" pulse />
        </div>
      </div>

      {/* Ornamental divider */}
      <div className="mt-3 flex items-center gap-3">
        <div className="h-px flex-1 bg-rule-strong" />
        <span className="font-display text-base italic text-brass">✦</span>
        <div className="h-px flex-1 bg-rule" />
      </div>

      {/* Wire ticker */}
      <div className="mt-2 flex h-7 items-center gap-3 overflow-hidden">
        <span className="label-cap shrink-0 text-brass">Wire</span>
        <div className="h-3 w-px shrink-0 bg-rule-strong" />
        <EventTicker events={events} />
      </div>

      {/* Closing rule */}
      <div className="mt-2 rule-double" />
    </header>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */

interface StatProps {
  label: string;
  value: string;
  accent: 'brass' | 'moss';
  pulse?: boolean;
}

function Stat({ label, value, accent, pulse }: StatProps) {
  const valueColor = accent === 'moss' ? 'text-moss' : 'text-bone';
  return (
    <div className="flex min-w-[88px] flex-col items-end justify-between border-l border-rule-strong px-3 py-1">
      <span className="label-cap">{label}</span>
      <span
        className={`numeric font-mono text-[20px] leading-none ${valueColor} flex items-center gap-1.5`}
      >
        {pulse && <Heartbeat />}
        {value}
      </span>
    </div>
  );
}

function Heartbeat() {
  const [on, setOn] = useState(true);
  useEffect(() => {
    const id = window.setInterval(() => setOn((v) => !v), 900);
    return () => window.clearInterval(id);
  }, []);
  return (
    <span
      aria-hidden
      className="inline-block h-1.5 w-1.5 rounded-full bg-moss transition-opacity duration-300"
      style={{ opacity: on ? 1 : 0.25, boxShadow: on ? '0 0 8px rgba(142,177,144,0.7)' : 'none' }}
    />
  );
}

/* ──────────────────────────────────────────────────────────────────────── */

interface PlateProps {
  number: string;
  title: string;
  caption?: string;
  className?: string;
  delay?: number;
  children: ReactNode;
}

function Plate({ number, title, caption, className = '', delay = 0, children }: PlateProps) {
  return (
    <section
      className={`plate animate-plate flex min-h-0 flex-col ${className}`}
      style={{ animationDelay: `${delay}s` }}
    >
      <span className="plate-corner tl" />
      <span className="plate-corner tr" />
      <span className="plate-corner bl" />
      <span className="plate-corner br" />

      <header className="flex items-baseline justify-between gap-3 border-b border-rule px-4 pt-2.5 pb-2">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-base italic leading-none text-brass-bright">
            Plate {number}.
          </span>
          <h2 className="font-display text-[22px] leading-none text-bone">{title}</h2>
        </div>
        {caption && (
          <span className="font-display text-xs italic text-bone-fade">{caption}</span>
        )}
      </header>

      <div className="relative min-h-0 flex-1 overflow-hidden">{children}</div>
    </section>
  );
}
