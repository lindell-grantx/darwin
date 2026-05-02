import type { EvolutionEvent } from '@contracts';

const COLOR: Record<EvolutionEvent['event_type'], string> = {
  'generation.evolved': 'text-emerald-400',
  'genome.born': 'text-sky-400',
  'genome.retired': 'text-zinc-400',
  'champion.promoted': 'text-amber-400',
  'query.completed': 'text-sky-300',
};

function summary(e: EvolutionEvent): string {
  switch (e.event_type) {
    case 'generation.evolved':
      return `gen ${e.generation} · best ${(e.data.best_fitness as number).toFixed(2)}`;
    case 'genome.born':
      return `new genome · gen ${e.generation}`;
    case 'genome.retired':
      return `retired · gen ${e.generation}`;
    case 'champion.promoted':
      return `champion ${e.data.champion_id as string} (fit ${(e.data.composite_fitness as number).toFixed(2)})`;
    case 'query.completed':
      return `query → ${e.data.genome_id as string} (fit ${(e.data.composite_fitness as number).toFixed(2)})`;
  }
}

interface Props {
  events: EvolutionEvent[];
}

export function EventTicker({ events }: Props) {
  const recent = events.slice(-6).reverse();
  return (
    <div className="flex items-center gap-3 overflow-hidden text-[11px]">
      <span className="text-zinc-500 uppercase tracking-wide">events</span>
      {recent.length === 0 && <span className="text-zinc-600">waiting…</span>}
      {recent.map((e, i) => (
        <span key={`${e.timestamp}-${i}`} className={`${COLOR[e.event_type]} font-mono whitespace-nowrap`}>
          {summary(e)}
        </span>
      ))}
    </div>
  );
}
