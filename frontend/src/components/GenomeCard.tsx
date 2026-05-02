import type { GenomeSummary } from '@contracts';

function fitnessColor(f: number): string {
  if (f >= 0.75) return 'text-emerald-400';
  if (f >= 0.55) return 'text-amber-400';
  return 'text-rose-400';
}

interface Props {
  genome: GenomeSummary;
  compact?: boolean;
}

export function GenomeCard({ genome, compact = false }: Props) {
  const { chunk_size, embedding_model } = genome.retrieval_genes;
  return (
    <div
      className={`rounded-md border border-zinc-800 bg-zinc-900/60 ${
        compact ? 'px-2 py-1 text-xs' : 'p-3 text-sm'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-zinc-300">{genome.id}</span>
        <span className={`font-mono font-semibold ${fitnessColor(genome.fitness.composite)}`}>
          {genome.fitness.composite.toFixed(2)}
        </span>
      </div>
      {!compact && (
        <div className="mt-1 text-xs text-zinc-500">
          gen {genome.generation} · {embedding_model} · k={chunk_size}
        </div>
      )}
    </div>
  );
}
