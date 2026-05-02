import { useEffect, useRef } from 'react';

import type { EvolutionEvent } from '@contracts';

const TONE: Record<EvolutionEvent['event_type'], string> = {
  'generation.evolved': 'text-moss',
  'genome.born': 'text-bone',
  'genome.retired': 'text-bone-fade',
  'champion.promoted': 'text-brass-bright',
  'query.completed': 'text-ember',
};

const SIGIL: Record<EvolutionEvent['event_type'], string> = {
  'generation.evolved': '⊕',
  'genome.born': '✦',
  'genome.retired': '†',
  'champion.promoted': '◆',
  'query.completed': '‡',
};

const LABEL: Record<EvolutionEvent['event_type'], string> = {
  'generation.evolved': 'EVOLVED',
  'genome.born': 'BORN',
  'genome.retired': 'RETIRED',
  'champion.promoted': 'CHAMPION',
  'query.completed': 'QUERY',
};

function summary(e: EvolutionEvent): string {
  switch (e.event_type) {
    case 'generation.evolved': {
      const fitness = e.data.best_fitness as number | undefined;
      return `gen ${e.generation} · best ${fitness != null ? fitness.toFixed(3) : '—'}`;
    }
    case 'genome.born':
      return `new specimen · gen ${e.generation}`;
    case 'genome.retired':
      return `expired · gen ${e.generation}`;
    case 'champion.promoted': {
      const fitness = e.data.composite_fitness as number | undefined;
      return `${e.data.champion_id as string} · fit ${fitness != null ? fitness.toFixed(3) : '—'}`;
    }
    case 'query.completed': {
      const fitness = e.data.composite_fitness as number | undefined;
      return `${e.data.genome_id as string} → fit ${fitness != null ? fitness.toFixed(3) : '—'}`;
    }
  }
}

function relTime(iso: string): string {
  const d = Date.now() - new Date(iso).getTime();
  if (d < 5_000) return 'now';
  if (d < 60_000) return `${Math.floor(d / 1000)}s`;
  if (d < 3_600_000) return `${Math.floor(d / 60_000)}m`;
  return `${Math.floor(d / 3_600_000)}h`;
}

interface Props {
  events: EvolutionEvent[];
}

export function EventTicker({ events }: Props) {
  const recent = events.slice(-8).reverse();
  const lastKey = recent[0] ? `${recent[0].timestamp}-${recent[0].event_type}` : '';
  const flashRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!flashRef.current) return;
    flashRef.current.classList.remove('ticker-flash');
    void flashRef.current.offsetWidth;
    flashRef.current.classList.add('ticker-flash');
  }, [lastKey]);

  if (recent.length === 0) {
    return (
      <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-bone-fade">
        awaiting first transmission
        <span className="ml-1 inline-block translate-y-[-1px]">
          <span className="blink-soft">_</span>
        </span>
      </span>
    );
  }

  return (
    <div className="flex min-w-0 flex-1 items-center gap-3 overflow-hidden">
      {recent.map((e, i) => {
        const isFirst = i === 0;
        return (
          <span
            ref={isFirst ? flashRef : undefined}
            key={`${e.timestamp}-${i}`}
            className="flex shrink-0 items-center gap-1.5 px-1.5 py-0.5 font-mono text-[11px] whitespace-nowrap"
          >
            <span className={`${TONE[e.event_type]} text-[12px] leading-none`}>
              {SIGIL[e.event_type]}
            </span>
            <span className={`${TONE[e.event_type]} tracking-[0.18em]`}>
              {LABEL[e.event_type]}
            </span>
            <span className="text-bone-dim">{summary(e)}</span>
            <span className="text-bone-fade">· {relTime(e.timestamp)}</span>
            {i < recent.length - 1 && <span className="ml-1.5 text-rule-strong">⁄</span>}
          </span>
        );
      })}
    </div>
  );
}
