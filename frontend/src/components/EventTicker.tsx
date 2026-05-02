import type { EvolutionEvent } from '@contracts';

const COLOR: Record<EvolutionEvent['type'], string> = {
  'evaluation.created': 'text-zinc-400',
  'generation.evolved': 'text-emerald-400',
  'champion.promoted': 'text-amber-400',
  'query.started': 'text-sky-400',
  'query.completed': 'text-sky-300',
};

function summary(e: EvolutionEvent): string {
  switch (e.type) {
    case 'evaluation.created':
      return `eval ${e.data.genome_id} → ${e.data.composite_fitness.toFixed(2)}`;
    case 'generation.evolved':
      return `gen ${e.data.generation} · best ${e.data.best_fitness.toFixed(2)} · ${e.data.n_offspring} offspring`;
    case 'champion.promoted':
      return `champion ${e.data.champion_id} (peak ${e.data.peak_fitness.toFixed(2)})`;
    case 'query.started':
      return `query ${e.data.run_id} · ${e.data.n_genomes} genomes`;
    case 'query.completed':
      return `query ${e.data.run_id} → ${e.data.winning_genome_id}`;
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
        <span key={`${e.timestamp}-${i}`} className={`${COLOR[e.type]} font-mono whitespace-nowrap`}>
          {summary(e)}
        </span>
      ))}
    </div>
  );
}
