import type { ReactNode } from 'react';

import { EventTicker } from './components/EventTicker';
import { FamilyTree } from './components/FamilyTree';
import { FitnessCurve } from './components/FitnessCurve';
import { LiveQuery } from './components/LiveQuery';
import { useEvolutionEvents } from './lib/sse';

export function App() {
  const events = useEvolutionEvents();
  const lastGen = [...events].reverse().find((e) => e.type === 'generation.evolved');
  const currentGen =
    lastGen && lastGen.type === 'generation.evolved' ? lastGen.data.generation : '—';

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-zinc-800 bg-zinc-900/40 px-4 py-2">
        <div className="flex items-baseline gap-3">
          <h1 className="text-base font-semibold tracking-tight">
            Darwin <span className="text-zinc-500 font-normal">· evolutionary retrieval</span>
          </h1>
          <span className="font-mono text-xs text-zinc-400">gen {currentGen}</span>
        </div>
        <EventTicker events={events} />
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-2 grid-rows-2 gap-3 p-3">
        <Panel title="Population & Family Tree" className="row-span-2">
          <div className="h-full min-h-0">
            <FamilyTree />
          </div>
        </Panel>
        <Panel title="Fitness Over Generations">
          <div className="h-full min-h-0">
            <FitnessCurve events={events} />
          </div>
        </Panel>
        <Panel title="Live Query">
          <LiveQuery />
        </Panel>
      </main>
    </div>
  );
}

interface PanelProps {
  title: string;
  className?: string;
  children: ReactNode;
}

function Panel({ title, className = '', children }: PanelProps) {
  return (
    <section
      className={`flex min-h-0 flex-col rounded-lg border border-zinc-800 bg-zinc-900/30 p-3 ${className}`}
    >
      <h2 className="mb-2 shrink-0 text-xs font-semibold uppercase tracking-wide text-zinc-400">
        {title}
      </h2>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}
