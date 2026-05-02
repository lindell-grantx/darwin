import { useRef, useState } from 'react';

import type { GenomeSummary, QueryResponse, RetrievalTraceItem } from '@contracts';

import { streamQuery } from '../lib/api';
import { GenomeCard } from './GenomeCard';
import { Markdown } from './Markdown';
import { SpecimenDossier } from './SpecimenDossier';
import { Spinner } from './Spinner';

const SUGGESTIONS = [
  'How do I tune Atlas Vector Search for 1M+ vectors?',
  'When should I use HNSW versus IVF for ANN?',
  'What is the right chunk size for technical docs?',
];

export function LiveQuery() {
  const [text, setText] = useState(SUGGESTIONS[0]);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedGenome, setSelectedGenome] = useState<GenomeSummary | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState('');
  const [streamingGenome, setStreamingGenome] = useState<GenomeSummary | null>(null);
  const [streamingChunks, setStreamingChunks] = useState<RetrievalTraceItem[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || loading) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);
    setStage('starting');
    setStreamingAnswer('');
    setStreamingGenome(null);
    setStreamingChunks([]);

    try {
      await streamQuery(
        text.trim(),
        {
          onProgress: (s) => setStage(s),
          onGenome: (g) => setStreamingGenome(g),
          onChunk: (c) =>
            setStreamingChunks((prev) => [
              ...prev,
              { chunk_id: c.chunk_id, score: c.score, position: c.position },
            ]),
          onToken: (delta) => setStreamingAnswer((prev) => prev + delta),
          onDone: (final) => {
            setResult(final);
            setStage(null);
          },
          onError: (msg) => setError(msg),
        },
        controller.signal,
      );
    } catch (err) {
      if (!controller.signal.aborted) setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Manuscript form */}
      <form onSubmit={submit} className="px-4 pt-3 pb-2.5">
        <label className="label-cap mb-1.5 flex items-center gap-2">
          <span className="font-display text-base italic leading-none text-brass-bright">?</span>
          Inquiry
        </label>
        <div className="group relative flex items-center border-b border-rule-strong transition-colors focus-within:border-brass-bright">
          <input
            className="flex-1 bg-transparent py-2 pr-3 font-display text-[18px] italic text-bone placeholder:text-bone-fade focus:outline-none"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Pose a question to the population…"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !text.trim()}
            className="ml-2 flex shrink-0 items-center gap-1.5 border border-brass-bright px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.28em] text-brass-bright transition-all hover:bg-brass-bright hover:text-ink-0 disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-brass-bright"
          >
            {loading ? <Spinner size="sm" /> : <span className="font-display italic">✦</span>}
            {loading ? 'consulting' : 'inquire'}
          </button>
        </div>
        {!result && !loading && (
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            <span className="label-cap mr-1">try</span>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setText(s)}
                className="border border-rule px-2 py-0.5 font-mono text-[10px] text-bone-dim transition-colors hover:border-brass hover:text-brass-bright"
              >
                {s.slice(0, 38)}
                {s.length > 38 ? '…' : ''}
              </button>
            ))}
          </div>
        )}
        {loading && stage && (
          <div className="mt-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-brass-bright">
            <Spinner size="sm" />
            <span>{stage}…</span>
          </div>
        )}
      </form>

      {error && (
        <div className="mx-4 mb-2 border border-oxblood/60 bg-oxblood-deep/30 px-3 py-2 font-mono text-[11px] text-oxblood">
          ⚠ {error}
        </div>
      )}

      {result ? (
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-3">
          <ResultBody result={result} onGenomeClick={setSelectedGenome} />
        </div>
      ) : loading ? (
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-3">
          <StreamingBody
            answer={streamingAnswer}
            genome={streamingGenome}
            chunks={streamingChunks}
            onGenomeClick={setSelectedGenome}
          />
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-1.5 px-6 text-center">
          <span className="font-display text-[28px] italic leading-tight text-bone-dim">
            awaiting inquiry
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-bone-fade">
            the population stands ready
          </span>
        </div>
      )}

      <SpecimenDossier genome={selectedGenome} onClose={() => setSelectedGenome(null)} />
    </div>
  );
}

function StreamingBody({
  answer,
  genome,
  chunks,
  onGenomeClick,
}: {
  answer: string;
  genome: GenomeSummary | null;
  chunks: RetrievalTraceItem[];
  onGenomeClick: (g: GenomeSummary) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {genome && (
        <section className="flex flex-col gap-1.5">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-xs italic text-brass-bright">§ i.</span>
            <span className="font-display text-sm text-bone">Working specimen</span>
          </div>
          <GenomeCard genome={genome} onClick={onGenomeClick} />
        </section>
      )}

      {chunks.length > 0 && (
        <section className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <div className="flex items-baseline gap-2">
              <span className="font-display text-xs italic text-brass-bright">§ ii.</span>
              <span className="font-display text-sm text-bone">Retrieval trace</span>
            </div>
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-bone-fade">
              {chunks.length} chunk{chunks.length === 1 ? '' : 's'}
            </span>
          </div>
          <div className="border border-rule">
            {chunks.map((c, i) => (
              <div
                key={`${c.chunk_id}-${i}`}
                className="grid grid-cols-[28px_1fr_56px_44px] gap-2 border-b border-rule/60 px-2 py-1 font-mono text-[11px] last:border-b-0"
              >
                <span className="text-right text-bone-fade">{String(i + 1).padStart(2, '0')}</span>
                <span className="truncate text-bone">{c.chunk_id}</span>
                <span className="numeric text-right text-moss">
                  {c.score != null ? c.score.toFixed(3) : '—'}
                </span>
                <span className="numeric text-right text-bone-dim">#{c.position ?? '—'}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <article className="relative border border-brass-dim/60 bg-gradient-to-b from-ink-2 to-ink-1 px-3.5 pt-3 pb-3.5">
        <div className="absolute -top-2 left-3.5 flex items-center gap-1.5 bg-ink-0 px-1.5">
          <span className="font-display text-xs italic text-brass-bright">◆</span>
          <span className="label-cap text-brass-bright">Drafting</span>
        </div>
        {answer ? (
          <div className="relative">
            <Markdown>{answer}</Markdown>
            <span className="ml-0.5 inline-block h-[1em] w-[2px] animate-pulse bg-brass-bright align-middle" />
          </div>
        ) : (
          <p className="font-display text-[14px] italic text-bone-fade">
            preparing the page…
          </p>
        )}
      </article>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */

function ResultBody({
  result,
  onGenomeClick,
}: {
  result: QueryResponse;
  onGenomeClick: (genome: GenomeSummary) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {/* Winning genome */}
      <Section title="Winning specimen" numeral="i">
        <GenomeCard genome={result.winning_genome} onClick={onGenomeClick} />
      </Section>

      {/* Retrieval trace */}
      <Section title="Retrieval trace" numeral="ii" caption={`${result.retrieval_trace.length} chunks`}>
        <div className="border border-rule">
          <div className="grid grid-cols-[28px_1fr_56px_44px] gap-2 border-b border-rule bg-ink-2/60 px-2 py-1 font-mono text-[9px] uppercase tracking-[0.2em] text-bone-fade">
            <span className="text-right">№</span>
            <span>chunk id</span>
            <span className="text-right">score</span>
            <span className="text-right">pos</span>
          </div>
          {result.retrieval_trace.map((r, i) => (
            <div
              key={r.chunk_id}
              className="grid grid-cols-[28px_1fr_56px_44px] gap-2 border-b border-rule/60 px-2 py-1 font-mono text-[11px] last:border-b-0"
            >
              <span className="text-right text-bone-fade">{String(i + 1).padStart(2, '0')}</span>
              <span className="truncate text-bone">{r.chunk_id}</span>
              <span className="numeric text-right text-moss">{r.score != null ? r.score.toFixed(3) : '—'}</span>
              <span className="numeric text-right text-bone-dim">#{r.position ?? '—'}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* Winning answer — sealed dispatch */}
      <article className="relative border border-brass-dim/60 bg-gradient-to-b from-ink-2 to-ink-1 px-3.5 pt-3 pb-3.5">
        <div className="absolute -top-2 left-3.5 flex items-center gap-1.5 bg-ink-0 px-1.5">
          <span className="font-display text-xs italic text-brass-bright">◆</span>
          <span className="label-cap text-brass-bright">Sealed dispatch</span>
        </div>
        <div className="mb-2 flex items-baseline justify-between gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-bone-fade">
            run · {result.run_id.slice(0, 12)}
          </span>
          <span className="numeric font-mono text-[10px] text-bone-fade">
            {Math.round(result.fitness.latency_ms)} ms
          </span>
        </div>
        <Markdown>{result.answer}</Markdown>
      </article>

      {/* Fitness ledger */}
      <Section title="Fitness ledger" numeral="iii">
        <FitnessLedger fitness={result.fitness} composite={result.composite_fitness} />
      </Section>
    </div>
  );
}

function Section({
  title,
  numeral,
  caption,
  children,
}: {
  title: string;
  numeral: string;
  caption?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="font-display text-xs italic text-brass-bright">§ {numeral}.</span>
          <span className="font-display text-sm text-bone">{title}</span>
        </div>
        {caption && (
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-bone-fade">
            {caption}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}

function FitnessLedger({
  fitness,
  composite,
}: {
  fitness: QueryResponse['fitness'];
  composite: number;
}) {
  const cells: Array<{ label: string; value: string; tone: string }> = [
    { label: 'relevance', value: fitness.relevance != null ? fitness.relevance.toFixed(3) : '—', tone: 'text-moss' },
    { label: 'accuracy', value: fitness.accuracy != null ? fitness.accuracy.toFixed(3) : '—', tone: 'text-moss' },
    { label: 'latency', value: fitness.latency_ms != null ? `${Math.round(fitness.latency_ms)} ms` : '—', tone: 'text-ember' },
    { label: 'cost', value: fitness.cost_usd != null ? `$${fitness.cost_usd.toFixed(4)}` : '—', tone: 'text-bone-dim' },
  ];
  return (
    <div className="border border-rule">
      <div className="flex items-baseline justify-between gap-2 border-b border-rule bg-ink-2/40 px-2.5 py-1.5">
        <span className="label-cap">Composite</span>
        <span className="numeric font-mono text-base font-semibold text-brass-bright">
          {composite != null ? composite.toFixed(3) : '—'}
        </span>
      </div>
      <div className="grid grid-cols-4">
        {cells.map((c, i) => (
          <div
            key={c.label}
            className={`flex flex-col gap-0.5 px-2.5 py-1.5 ${i < cells.length - 1 ? 'border-r border-rule' : ''}`}
          >
            <span className="label-cap">{c.label}</span>
            <span className={`numeric font-mono text-sm font-medium ${c.tone}`}>
              {c.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
