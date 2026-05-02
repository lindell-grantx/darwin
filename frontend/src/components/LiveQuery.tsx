import { useState } from 'react';

import type { QueryResponse } from '@contracts';

import { postQuery } from '../lib/api';
import { GenomeCard } from './GenomeCard';
import { Spinner } from './Spinner';

export function LiveQuery() {
  const [text, setText] = useState('How do I tune Atlas Vector Search for 1M+ vectors?');
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await postQuery(text.trim());
      setResult(res);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden">
      <form onSubmit={submit} className="flex gap-2">
        <input
          className="flex-1 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-emerald-500"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask the population…"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {loading && <Spinner size="sm" />}
          {loading ? 'Running…' : 'Run'}
        </button>
      </form>

      {error && <div className="text-xs text-rose-400">{error}</div>}

      {result && (
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
          <div className="rounded-md border border-emerald-700/40 bg-emerald-950/30 p-3">
            <div className="mb-1 text-[11px] uppercase tracking-wide text-emerald-300">
              Winning answer · {Math.round(result.fitness.latency_ms)} ms
            </div>
            <div className="whitespace-pre-wrap text-sm text-zinc-100">{result.answer}</div>
          </div>

          <div>
            <div className="mb-1 text-[11px] uppercase tracking-wide text-zinc-400">
              Winning genome
            </div>
            <GenomeCard genome={result.winning_genome} />
          </div>

          <div>
            <div className="mb-1 text-[11px] uppercase tracking-wide text-zinc-400">
              Fitness breakdown
            </div>
            <FitnessGrid fitness={result.fitness} />
          </div>

          <div>
            <div className="mb-1 text-[11px] uppercase tracking-wide text-zinc-400">
              Retrieval trace ({result.retrieval_trace.length} chunks)
            </div>
            <div className="space-y-1">
              {result.retrieval_trace.map((r) => (
                <div
                  key={r.chunk_id}
                  className="flex items-center justify-between rounded border border-zinc-800 bg-zinc-900/40 px-2 py-1 font-mono text-xs text-zinc-300"
                >
                  <span>{r.chunk_id}</span>
                  <span className="text-zinc-400">
                    score {r.score.toFixed(3)} · #{r.position}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FitnessGrid({ fitness }: { fitness: QueryResponse['fitness'] }) {
  const cells: Array<[string, string]> = [
    ['relevance', fitness.relevance.toFixed(2)],
    ['accuracy', fitness.accuracy.toFixed(2)],
    ['latency', `${Math.round(fitness.latency_ms)} ms`],
    ['cost', `$${fitness.cost_usd.toFixed(4)}`],
  ];
  return (
    <div className="grid grid-cols-4 gap-2">
      {cells.map(([label, val]) => (
        <div key={label} className="rounded border border-zinc-800 bg-zinc-900/40 px-2 py-1">
          <div className="text-[10px] uppercase text-zinc-500">{label}</div>
          <div className="font-mono text-xs text-zinc-200">{val}</div>
        </div>
      ))}
    </div>
  );
}
