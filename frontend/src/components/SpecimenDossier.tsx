import { useEffect } from 'react';

import type { GenomeSummary } from '@contracts';

interface Props {
  genome: GenomeSummary | null;
  onClose: () => void;
}

export function SpecimenDossier({ genome, onClose }: Props) {
  useEffect(() => {
    if (!genome) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [genome, onClose]);

  if (!genome) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end">
      <button
        aria-label="Close dossier"
        onClick={onClose}
        className="animate-backdrop absolute inset-0 cursor-default bg-ink-0/55 backdrop-blur-[2px]"
      />
      <DossierPanel genome={genome} onClose={onClose} />
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */

function DossierPanel({ genome, onClose }: { genome: GenomeSummary; onClose: () => void }) {
  const tier = tierFor(genome.fitness.composite);
  const isChamp = genome.status === 'champion';

  return (
    <aside
      role="dialog"
      aria-modal="true"
      aria-label={`Specimen dossier ${genome.id}`}
      className="animate-drawer relative flex h-full w-[460px] max-w-full flex-col border-l border-rule-strong bg-ink-1 shadow-[-30px_0_60px_-20px_rgba(0,0,0,0.7)]"
    >
      <span className="plate-corner tl" />
      <span className="plate-corner bl" />

      {/* Header */}
      <header className="relative shrink-0 border-b border-rule px-5 pt-5 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="label-cap mb-1 flex items-center gap-1.5 tracking-[0.28em]">
              <span className="font-display italic text-brass-bright">§</span>
              Specimen Dossier
            </span>
            <h2 className="font-display text-[40px] italic leading-[0.95] tracking-tight text-bone">
              {genome.id}
            </h2>
            <div className="mt-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em]">
              <StatusPill status={genome.status} isChamp={isChamp} />
              <span className="text-bone-fade">·</span>
              <span className="text-bone-dim">gen {genome.generation}</span>
              <span className="text-bone-fade">·</span>
              <span className={tier.text}>{tier.label}</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="font-display flex h-8 w-8 items-center justify-center border border-rule text-xl leading-none text-bone-dim transition-colors hover:border-brass-bright hover:text-brass-bright"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Composite fitness ring */}
        <div className="mt-4 flex items-center gap-4">
          <FitnessRing value={genome.fitness.composite} />
          <div className="flex flex-col">
            <span className="label-cap">Composite fitness</span>
            <span className={`numeric font-display text-[36px] italic leading-none ${tier.text}`}>
              {genome.fitness.composite.toFixed(3)}
            </span>
            <span className="font-mono text-[10px] tracking-[0.18em] text-bone-fade">
              n = {genome.fitness.n_evaluations} evaluation
              {genome.fitness.n_evaluations === 1 ? '' : 's'}
              {genome.fitness.last_updated && (
                <> · upd {relTime(genome.fitness.last_updated)}</>
              )}
            </span>
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        <DossierSection title="Retrieval genes" numeral="i">
          <Row k="embedding_model" v={genome.retrieval_genes?.embedding_model ?? '—'} mono />
          <Row
            k="chunk_size"
            v={genome.retrieval_genes?.chunk_size != null ? `${genome.retrieval_genes.chunk_size} tok` : '—'}
            num
          />
          <Row
            k="chunk_overlap"
            v={genome.retrieval_genes?.chunk_overlap != null ? `${(genome.retrieval_genes.chunk_overlap * 100).toFixed(0)} %` : '—'}
            num
          />
          <Row k="query_transform" v={genome.retrieval_genes?.query_transform ?? '—'} pill />
          <Row k="rerank" v={genome.retrieval_genes?.rerank ?? '—'} pill />
          <Row
            k="confidence_thr"
            v={genome.retrieval_genes?.confidence_threshold != null ? genome.retrieval_genes.confidence_threshold.toFixed(2) : '—'}
            num
          />
          <Row k="top_k" v={genome.retrieval_genes?.top_k != null ? String(genome.retrieval_genes.top_k) : '—'} num />
          <Row
            k="source_routing"
            v={genome.retrieval_genes?.source_routing?.length ? genome.retrieval_genes.source_routing.join(' · ') : '—'}
            mono
          />
        </DossierSection>

        <DossierSection title="Coordination genes" numeral="ii">
          <Row k="protocol" v={genome.coordination_genes?.protocol ?? '—'} pill />
          <Row
            k="consult_thr"
            v={genome.coordination_genes?.consult_threshold != null ? genome.coordination_genes.consult_threshold.toFixed(2) : '—'}
            num
          />
          <Row
            k="timeout_ms"
            v={genome.coordination_genes?.timeout_ms != null ? `${genome.coordination_genes.timeout_ms.toLocaleString()} ms` : '—'}
            num
          />
          <Row
            k="debate_rounds"
            v={genome.coordination_genes?.debate_rounds != null ? String(genome.coordination_genes.debate_rounds) : '—'}
            num
          />
        </DossierSection>

        <DossierSection title="Generation genes" numeral="iii">
          <Row k="model" v={genome.generation_genes?.model ?? '—'} mono />
          <Row k="temperature" v={genome.generation_genes?.temperature != null ? genome.generation_genes.temperature.toFixed(2) : '—'} num />
          <Row
            k="max_tokens"
            v={genome.generation_genes?.max_tokens != null ? genome.generation_genes.max_tokens.toLocaleString() : '—'}
            num
          />
          <Row k="system_style" v={genome.generation_genes?.system_style ?? '—'} pill />
        </DossierSection>
      </div>

      <footer className="shrink-0 border-t border-rule px-5 py-2.5">
        <div className="flex items-center justify-between gap-3 font-mono text-[10px] uppercase tracking-[0.24em] text-bone-fade">
          <span>esc to close</span>
          <span className="font-display italic text-brass">— D —</span>
        </div>
      </footer>
    </aside>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */

function StatusPill({
  status,
  isChamp,
}: {
  status: GenomeSummary['status'];
  isChamp: boolean;
}) {
  if (isChamp) {
    return (
      <span className="border border-brass-bright/70 bg-brass-bright/10 px-1.5 py-px font-mono text-[10px] tracking-[0.22em] text-brass-bright">
        ◆ champion
      </span>
    );
  }
  if (status === 'retired') {
    return (
      <span className="border border-rule px-1.5 py-px font-mono text-[10px] tracking-[0.22em] text-bone-fade">
        † retired
      </span>
    );
  }
  return (
    <span className="border border-moss/40 bg-moss-deep/30 px-1.5 py-px font-mono text-[10px] tracking-[0.22em] text-moss">
      ✦ alive
    </span>
  );
}

function tierFor(f: number): { label: string; text: string; stroke: string } {
  if (f >= 0.75)
    return { label: 'apex', text: 'text-moss', stroke: 'var(--color-moss)' };
  if (f >= 0.55)
    return { label: 'viable', text: 'text-ember', stroke: 'var(--color-ember)' };
  return { label: 'frail', text: 'text-oxblood', stroke: 'var(--color-oxblood)' };
}

function FitnessRing({ value }: { value: number }) {
  const r = 30;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - Math.max(0, Math.min(1, value)));
  const stroke = tierFor(value).stroke;
  return (
    <svg
      width={72}
      height={72}
      viewBox="0 0 72 72"
      aria-hidden
      className="shrink-0"
    >
      <circle
        cx={36}
        cy={36}
        r={r}
        fill="none"
        stroke="var(--color-rule-strong)"
        strokeWidth={2}
      />
      <circle
        cx={36}
        cy={36}
        r={r}
        fill="none"
        stroke={stroke}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={offset}
        transform="rotate(-90 36 36)"
        style={{
          filter: `drop-shadow(0 0 4px ${stroke})`,
          transition: 'stroke-dashoffset 0.7s cubic-bezier(.2,.8,.2,1)',
        }}
      />
      <text
        x={36}
        y={40}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
        fontSize={11}
        fill="var(--color-bone)"
        style={{ letterSpacing: '0.05em' }}
      >
        {Math.round(value * 100)}%
      </text>
    </svg>
  );
}

function DossierSection({
  title,
  numeral,
  children,
}: {
  title: string;
  numeral: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-5 last:mb-0">
      <header className="mb-2 flex items-baseline gap-2 border-b border-rule pb-1">
        <span className="font-display text-sm italic text-brass-bright">§ {numeral}.</span>
        <h3 className="font-display text-base text-bone">{title}</h3>
      </header>
      <dl className="grid grid-cols-[140px_1fr] gap-y-px">{children}</dl>
    </section>
  );
}

interface RowProps {
  k: string;
  v: string;
  num?: boolean;
  mono?: boolean;
  pill?: boolean;
}

function Row({ k, v, num, mono, pill }: RowProps) {
  return (
    <>
      <dt className="border-b border-rule/60 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-bone-fade">
        {k}
      </dt>
      <dd className="flex items-center justify-end border-b border-rule/60 py-1.5 text-right">
        {pill ? (
          <span className="border border-rule-strong bg-ink-2 px-1.5 py-px font-mono text-[11px] tracking-[0.18em] text-bone">
            {v}
          </span>
        ) : (
          <span
            className={`${mono || num ? 'font-mono' : ''} ${num ? 'numeric' : ''} text-[12px] text-bone`}
          >
            {v}
          </span>
        )}
      </dd>
    </>
  );
}

function relTime(iso: string): string {
  const d = Date.now() - new Date(iso).getTime();
  if (d < 5_000) return 'just now';
  if (d < 60_000) return `${Math.floor(d / 1000)}s ago`;
  if (d < 3_600_000) return `${Math.floor(d / 60_000)}m ago`;
  if (d < 86_400_000) return `${Math.floor(d / 3_600_000)}h ago`;
  return new Date(iso).toLocaleDateString();
}
