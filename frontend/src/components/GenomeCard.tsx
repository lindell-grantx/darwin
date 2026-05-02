import type { GenomeSummary } from '@contracts';

function fitnessTone(f: number): { text: string; bar: string } {
  if (f >= 0.75) return { text: 'text-moss', bar: 'var(--color-moss)' };
  if (f >= 0.55) return { text: 'text-ember', bar: 'var(--color-ember)' };
  return { text: 'text-oxblood', bar: 'var(--color-oxblood)' };
}

interface Props {
  genome: GenomeSummary;
  compact?: boolean;
  onClick?: (genome: GenomeSummary) => void;
}

export function GenomeCard({ genome, compact = false, onClick }: Props) {
  const { chunk_size, embedding_model, top_k } = genome.retrieval_genes ?? {};
  const tone = fitnessTone(genome.fitness?.composite ?? 0);
  const isChamp = genome.status === 'champion';

  const Wrapper = onClick ? 'button' : 'div';
  const wrapperProps = onClick
    ? {
        type: 'button' as const,
        onClick: () => onClick(genome),
        className: `lift relative border border-rule bg-ink-1 transition-all hover:scale-[1.01] hover:border-brass-bright active:scale-[0.99] ${
          compact ? 'px-2 py-1.5' : 'px-3 py-2.5'
        }`,
      }
    : {
        className: `lift relative border border-rule bg-ink-1 ${
          compact ? 'px-2 py-1.5' : 'px-3 py-2.5'
        }`,
      };

  return (
    <Wrapper {...wrapperProps}>
      {isChamp && (
        <span className="absolute -top-1.5 left-2.5 bg-ink-0 px-1 font-display text-[10px] italic leading-none text-brass-bright">
          ◆ champion
        </span>
      )}

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="label-cap">Specimen</span>
          <span className="font-mono text-[13px] text-bone">{genome.id}</span>
        </div>
        <span className={`numeric font-mono text-base font-semibold ${tone.text}`}>
          {genome.fitness?.composite != null ? genome.fitness.composite.toFixed(2) : '—'}
        </span>
      </div>

      {!compact && (
        <>
          <div className="bar-track mt-1.5 h-[2px] w-full overflow-hidden">
            <div
              className="h-full transition-[width] duration-700"
              style={{
                width: `${Math.max(4, (genome.fitness?.composite ?? 0) * 100)}%`,
                background: tone.bar,
                boxShadow: `0 0 6px ${tone.bar}`,
              }}
            />
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2 font-mono text-[10px]">
            <Field label="gen" value={String(genome.generation ?? '—')} />
            <Field label="model" value={embedding_model ?? '—'} />
            <Field label="chunk·k" value={chunk_size != null && top_k != null ? `${chunk_size}·${top_k}` : '—'} />
          </div>
        </>
      )}
    </Wrapper>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="label-cap">{label}</span>
      <span className="truncate text-bone">{value}</span>
    </div>
  );
}
