import {
  Background,
  Controls,
  type Edge,
  MiniMap,
  type Node,
  ReactFlow,
} from '@xyflow/react';
import { useEffect, useMemo, useState } from 'react';

import type { GenomeSummary, LineageResponse, PopulationResponse } from '@contracts';

import { getLineage, getPopulation } from '../lib/api';

const NODE_W = 140;
const NODE_H = 56;
const COL_GAP = 200;
const ROW_GAP = 90;

function fitnessTint(f: number): string {
  if (f >= 0.75) return '#064e3b'; // emerald-950
  if (f >= 0.55) return '#451a03'; // amber-950
  return '#450a0a'; // rose-950
}
function fitnessBorder(f: number): string {
  if (f >= 0.75) return '#10b981';
  if (f >= 0.55) return '#f59e0b';
  return '#f43f5e';
}

interface BuiltGraph {
  nodes: Node[];
  edges: Edge[];
}

function buildGraph(population: PopulationResponse, lineages: LineageResponse[]): BuiltGraph {
  const byId = new Map<string, GenomeSummary>();
  for (const g of population.genomes) byId.set(g.id, g);
  for (const l of lineages) {
    byId.set(l.genome.id, l.genome);
    for (const a of l.ancestors) byId.set(a.genome.id, a.genome);
  }

  // Layout: y = generation, x = index within generation.
  const byGen = new Map<number, GenomeSummary[]>();
  for (const g of byId.values()) {
    const list = byGen.get(g.generation) ?? [];
    list.push(g);
    byGen.set(g.generation, list);
  }
  for (const list of byGen.values()) list.sort((a, b) => a.id.localeCompare(b.id));

  const nodes: Node[] = [];
  for (const [gen, list] of byGen.entries()) {
    list.forEach((g, i) => {
      const offset = (list.length - 1) / 2;
      nodes.push({
        id: g.id,
        position: { x: (i - offset) * COL_GAP, y: gen * ROW_GAP },
        data: {
          label: (
            <div className="leading-tight">
              <div className="font-mono text-[11px] text-zinc-200">{g.id}</div>
              <div className="font-mono text-[10px] text-zinc-400">
                fit {g.fitness_composite.toFixed(2)} · k={String(g.retrieval_genes.k)}
              </div>
            </div>
          ),
        },
        style: {
          width: NODE_W,
          height: NODE_H,
          background: fitnessTint(g.fitness_composite),
          border: `1px solid ${fitnessBorder(g.fitness_composite)}`,
          borderRadius: 6,
          color: '#e4e4e7',
          padding: 6,
          fontSize: 11,
        },
      });
    });
  }

  const edgeSet = new Set<string>();
  const edges: Edge[] = [];
  for (const l of lineages) {
    let childId = l.genome.id;
    for (const a of l.ancestors) {
      const key = `${a.genome.id}->${childId}`;
      if (!edgeSet.has(key)) {
        edgeSet.add(key);
        edges.push({
          id: key,
          source: a.genome.id,
          target: childId,
          style: { stroke: '#52525b' },
          animated: false,
        });
      }
      childId = a.genome.id;
    }
  }

  return { nodes, edges };
}

export function FamilyTree() {
  const [population, setPopulation] = useState<PopulationResponse | null>(null);
  const [lineages, setLineages] = useState<LineageResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const pop = await getPopulation();
        if (!mounted) return;
        setPopulation(pop);
        // Fetch lineages for the top-3 fittest to draw edges.
        const top = [...pop.genomes]
          .sort((a, b) => b.fitness_composite - a.fitness_composite)
          .slice(0, 3);
        const lins = await Promise.all(top.map((g) => getLineage(g.id)));
        if (mounted) setLineages(lins);
      } catch (err) {
        if (mounted) setError(String(err));
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const graph = useMemo(
    () => (population ? buildGraph(population, lineages) : { nodes: [], edges: [] }),
    [population, lineages],
  );

  if (error) return <div className="text-xs text-rose-400">{error}</div>;
  if (!population) return <div className="text-xs text-zinc-500">Loading population…</div>;

  return (
    <ReactFlow
      nodes={graph.nodes}
      edges={graph.edges}
      fitView
      proOptions={{ hideAttribution: true }}
      nodesDraggable={false}
      nodesConnectable={false}
    >
      <Background color="#27272a" gap={18} />
      <Controls className="!bg-zinc-900 !border-zinc-700" showInteractive={false} />
      <MiniMap
        nodeColor={(n) => (n.style?.background as string) ?? '#3f3f46'}
        maskColor="rgba(0,0,0,0.6)"
        style={{ backgroundColor: '#18181b' }}
        pannable
      />
    </ReactFlow>
  );
}
