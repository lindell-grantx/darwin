import { Hono } from 'hono';
import { streamSSE } from 'hono/streaming';
import type {
  CoordinationGenes,
  GenerationGenes,
  GenomeStatus,
  GenomeSummary,
  QueryRequest,
  QueryResponse,
  QueryRoutingInfo,
  RetrievalGenes,
  RetrievalTraceItem,
} from '../../../src/contracts.ts';
import { env } from '../env.ts';

export const query = new Hono();

// Upstream SSE event payloads (from Python /evaluate-stream).
interface PyGenomeEvent {
  id: string;
  generation: number;
  status?: GenomeStatus;
  retrieval_genes: RetrievalGenes;
  coordination_genes: CoordinationGenes;
  generation_genes: GenerationGenes;
  composite_fitness: number;
}

interface PyChunkEvent {
  chunk_id: string;
  score: number;
  position: number;
  text_preview?: string;
}

// Loose shape for the routing block the Python worker / evaluate-stream may
// emit. Each field is optional + nullable: a stream from a pre-Nash deployment
// (or the genesis state where no Nash strategy / no buckets exist yet) will
// simply omit it, and Hono surfaces nulls in that case.
interface PyRoutingEvent {
  bucket_key?: string[] | null;
  cosine?: number | null;
  bucket_cosine?: number | null;
  nash_strategy_id?: string | null;
  sampled_defender_id?: string | null;
}

interface PyDoneEvent {
  run_id: string;
  answer: string;
  composite_fitness: number;
  fitness: QueryResponse['fitness'];
  rationale?: string;
  timestamp?: string;
  routing?: PyRoutingEvent | null;
}

function buildWinningGenome(g: PyGenomeEvent, runFitness: number): GenomeSummary {
  return {
    id: g.id,
    generation: g.generation,
    status: g.status ?? 'alive',
    fitness: {
      composite: runFitness,
      n_evaluations: 1,
      last_updated: new Date().toISOString(),
    },
    retrieval_genes: g.retrieval_genes,
    coordination_genes: g.coordination_genes,
    generation_genes: g.generation_genes,
  };
}

const log = (msg: string, extra?: Record<string, unknown>) => {
  const ts = new Date().toISOString();
  if (extra) console.log(`[query] ${ts} ${msg}`, extra);
  else console.log(`[query] ${ts} ${msg}`);
};

// POST /query — SSE pass-through to the Python /evaluate-stream pipeline.
// Forwards progress / chunk / token / error events verbatim, accumulates
// genome + chunks, and emits a final `done` event with a fully-shaped
// QueryResponse (so the client has one canonical payload to render).
query.post('/', async (c) => {
  const body = await c.req.json<QueryRequest>();

  if (!body.text?.trim()) {
    return c.json({ error: 'empty_query' }, 400);
  }

  const started = Date.now();
  log('request received', { text_len: body.text.length, text_head: body.text.slice(0, 80) });

  // Defeat reverse-proxy buffering (nginx, Cloud Run, etc.).
  c.header('X-Accel-Buffering', 'no');
  c.header('Cache-Control', 'no-cache, no-transform');

  return streamSSE(c, async (stream) => {
    let upstream: Response;
    try {
      log('fetching upstream', { url: `${env.PYTHON_SERVICE_URL}/evaluate-stream` });
      upstream = await fetch(`${env.PYTHON_SERVICE_URL}/evaluate-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          text: body.text,
          genome_id: null,
          persist: true,
        }),
      });
      log('upstream connected', {
        status: upstream.status,
        content_type: upstream.headers.get('content-type'),
        transfer_encoding: upstream.headers.get('transfer-encoding'),
        has_body: !!upstream.body,
      });
    } catch (err) {
      log('upstream fetch failed', { error: err instanceof Error ? err.message : String(err) });
      await stream.writeSSE({
        event: 'error',
        data: JSON.stringify({
          message: `upstream_unreachable: ${err instanceof Error ? err.message : String(err)}`,
        }),
      });
      return;
    }

    if (!upstream.ok || !upstream.body) {
      const errText = await upstream.text().catch(() => '');
      log('upstream rejected', { status: upstream.status, body_head: errText.slice(0, 200) });
      await stream.writeSSE({
        event: 'error',
        data: JSON.stringify({
          message: `python_service_${upstream.status}: ${errText.slice(0, 500)}`,
        }),
      });
      return;
    }

    let genome: PyGenomeEvent | null = null;
    const trace: RetrievalTraceItem[] = [];

    const reader = upstream.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let chunkCount = 0;
    let bytesIn = 0;
    let eventsForwarded = 0;
    const eventCounts: Record<string, number> = {};

    try {
      while (!stream.aborted) {
        const { value, done } = await reader.read();
        if (done) {
          log('upstream stream ended', {
            chunks_read: chunkCount,
            bytes_in: bytesIn,
            events_forwarded: eventsForwarded,
            event_counts: eventCounts,
            elapsed_ms: Date.now() - started,
          });
          break;
        }
        chunkCount += 1;
        bytesIn += value.byteLength;
        buffer += decoder.decode(value, { stream: true });
        log('upstream chunk', {
          n: chunkCount,
          bytes: value.byteLength,
          buf_len: buffer.length,
        });

        // SSE events are separated by a blank line. Tolerate LF or CRLF.
        while (true) {
          const match = buffer.match(/\r?\n\r?\n/);
          if (!match || match.index === undefined) break;
          const rawEvent = buffer.slice(0, match.index);
          buffer = buffer.slice(match.index + match[0].length);

          let eventName: string | undefined;
          const dataLines: string[] = [];
          for (const line of rawEvent.split(/\r?\n/)) {
            if (line.startsWith(':')) continue; // SSE comment
            if (line.startsWith('event:')) eventName = line.slice(6).replace(/^ /, '');
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
          }
          if (dataLines.length === 0) continue;
          const dataStr = dataLines.join('\n');
          const evKey = eventName ?? 'message';
          eventCounts[evKey] = (eventCounts[evKey] ?? 0) + 1;

          // Side effects on accumulators before forwarding.
          if (eventName === 'genome') {
            try {
              genome = JSON.parse(dataStr) as PyGenomeEvent;
              log('parsed genome', { id: genome.id, generation: genome.generation });
            } catch (err) {
              log('genome parse failed', { error: String(err) });
            }
          } else if (eventName === 'chunk') {
            try {
              const ch = JSON.parse(dataStr) as PyChunkEvent;
              trace.push({
                chunk_id: ch.chunk_id,
                score: ch.score,
                position: ch.position,
              });
            } catch (err) {
              log('chunk parse failed', { error: String(err) });
            }
          } else if (eventName === 'done') {
            try {
              const py = JSON.parse(dataStr) as PyDoneEvent;
              const r = py.routing ?? null;
              const routing: QueryRoutingInfo = {
                bucket_key: r?.bucket_key ?? null,
                bucket_cosine: r?.bucket_cosine ?? r?.cosine ?? null,
                nash_strategy_id: r?.nash_strategy_id ?? null,
                sampled_defender_id: r?.sampled_defender_id ?? null,
              };
              const finalResponse: QueryResponse = {
                run_id: py.run_id,
                answer: py.answer,
                winning_genome: genome
                  ? buildWinningGenome(genome, py.composite_fitness)
                  : ({
                      id: 'unknown',
                      generation: 0,
                      status: 'alive',
                      fitness: {
                        composite: py.composite_fitness,
                        n_evaluations: 1,
                        last_updated: new Date().toISOString(),
                      },
                    } as GenomeSummary),
                fitness: py.fitness,
                composite_fitness: py.composite_fitness,
                retrieval_trace: trace,
                routing,
              };
              log('emitting done', {
                run_id: py.run_id,
                composite_fitness: py.composite_fitness,
                trace_len: trace.length,
                has_genome: !!genome,
                has_routing: !!py.routing,
                routing_bucket: routing.bucket_key,
                routing_defender: routing.sampled_defender_id,
                elapsed_ms: Date.now() - started,
              });
              await stream.writeSSE({
                event: 'done',
                data: JSON.stringify(finalResponse),
              });
              eventsForwarded += 1;
              continue; // already forwarded — skip the verbatim forward below
            } catch (err) {
              log('done reshape failed, forwarding verbatim', { error: String(err) });
            }
          }

          if (eventName === 'token') {
            // High-volume — log a one-liner without payload to avoid spam.
            try {
              const { delta } = JSON.parse(dataStr) as { delta: string };
              log('forward token', { len: delta?.length ?? 0 });
            } catch {
              log('forward token (unparsed)');
            }
          } else {
            log('forward event', { event: eventName, data_len: dataStr.length });
          }

          await stream.writeSSE({
            event: eventName,
            data: dataStr,
          });
          eventsForwarded += 1;
        }
      }
      if (stream.aborted) log('client aborted', { events_forwarded: eventsForwarded });
    } catch (err) {
      log('proxy error', { error: err instanceof Error ? err.message : String(err) });
      console.error('[POST /query] proxy error:', err);
      await stream.writeSSE({
        event: 'error',
        data: JSON.stringify({
          message: `proxy_error: ${err instanceof Error ? err.message : String(err)}`,
        }),
      });
    } finally {
      try {
        reader.releaseLock();
      } catch {
        // already released
      }
      log('handler done', { elapsed_ms: Date.now() - started });
    }
  });
});
