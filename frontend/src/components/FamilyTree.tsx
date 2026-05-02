import {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  Handle,
  type Node,
  type NodeProps,
  type NodeTypes,
  Position,
  ReactFlow,
} from '@xyflow/react';
import { useEffect, useMemo, useState } from 'react';

import type {
  GenomeSummary,
  LineageResponse,
  PopulationResponse,
} from '@contracts';

import { getLineage, getPopulation } from '../lib/api';
import { SpecimenDossier } from './SpecimenDossier';
import { Spinner } from './Spinner';

const NODE_W = 168;
const NODE_H = 76;
const COL_GAP = 210;
const ROW_GAP = 110;

type Tier = 'apex' | 'viable' | 'frail';
function fitnessTier(f: number): Tier {
  if (f >= 0.75) return 'apex';
  if (f >= 0.55) return 'viable';
  return 'frail';
}

// GraphNode can be a full GenomeSummary from population or a partial from lineage
type GraphNode = GenomeSummary;

interface BuiltGraph {
  nodes: Node[];
  edges: Edge[];
  championIds: Set<string>;
}

interface GenomeNodeData {
  genome: GraphNode;
  isChampion: boolean;
  onClick: (genome: GraphNode) => void;
  [key: string]: unknown;
}

function buildGraph(
  population: PopulationResponse,
  lineages: LineageResponse[],
  onClick: (genome: GraphNode) => void,
): BuiltGraph {
  const byId = new Map<string, GraphNode>();
  for (const g of population.genomes) byId.set(g.id, g);
  for (const l of lineages) {
    for (const n of l.nodes) {
      // Convert LineageNode to GenomeSummary by adding missing fields
      // These fields won't be displayed for lineage-only nodes anyway
      const genome: GenomeSummary = {
        id: n.id,
        generation: n.generation,
        status: n.is_champion ? 'champion' : 'alive',
        fitness: n.fitness,
        retrieval_genes: n.retrieval_genes,
        coordination_genes: {
          protocol: 'solo',
          consult_threshold: 0,
          timeout_ms: 0,
          debate_rounds: 0,
        },
        generation_genes: {
          model: 'claude-sonnet-4-6',
          temperature: 0,
          max_tokens: 0,
          system_style: 'concise',
        },
      };
      byId.set(n.id, genome);
    }
  }

  const championIds = new Set<string>();
  for (const l of lineages) {
    for (const n of l.nodes) if (n.is_champion) championIds.add(n.id);
  }

  const byGen = new Map<number, GraphNode[]>();
  for (const g of byId.values()) {
    const list = byGen.get(g.generation) ?? [];
    list.push(g);
    byGen.set(g.generation, list);
  }
  for (const list of byGen.values()) {
    list.sort((a, b) => b.fitness.composite - a.fitness.composite);
  }

  const nodes: Node[] = [];
  for (const [gen, list] of byGen.entries()) {
    list.forEach((g, i) => {
      const offset = (list.length - 1) / 2;
      nodes.push({
        id: g.id,
        type: 'genome',
        position: { x: (i - offset) * COL_GAP, y: gen * ROW_GAP },
        data: {
          genome: g,
          isChampion: championIds.has(g.id),
          onClick,
        } satisfies GenomeNodeData,
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
        draggable: false,
        connectable: false,
      });
    });
  }

  const edgeSet = new Set<string>();
  const edges: Edge[] = [];
  for (const l of lineages) {
    for (const node of l.nodes) {
      for (const parentId of node.parent_ids) {
        const key = `${parentId}->${node.id}`;
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          edges.push({
            id: key,
            source: parentId,
            target: node.id,
            type: 'smoothstep',
            animated: false,
          });
        }
      }
    }
  }

  return { nodes, edges, championIds };
}

/* ──────────────────────────────────────────────────────────────────────── */

function GenomeNode({ data }: NodeProps) {
  const { genome, isChampion, onClick } = data as GenomeNodeData;
  const fitness = genome.fitness.composite;
  const tier = fitnessTier(fitness);

  const tierBorder =
    tier === 'apex'
      ? 'border-moss/60'
      : tier === 'viable'
        ? 'border-ember/50'
        : 'border-oxblood/50';

  const tierTone =
    tier === 'apex' ? 'text-moss' : tier === 'viable' ? 'text-ember' : 'text-oxblood';

  const barColor =
    tier === 'apex'
      ? 'var(--color-moss)'
      : tier === 'viable'
        ? 'var(--color-ember)'
        : 'var(--color-oxblood)';

  return (
    <button
      type="button"
      onClick={() => onClick(genome)}
      className={`group relative flex h-full w-full cursor-pointer flex-col gap-1 border bg-gradient-to-b from-ink-2/90 to-ink-1 px-2.5 py-2 transition-all hover:scale-[1.02] hover:shadow-[0_4px_16px_-6px_rgba(212,164,74,0.4)] active:scale-[0.98] ${tierBorder} ${
        isChampion ? 'ring-1 ring-brass-bright/70 ring-offset-2 ring-offset-ink-0' : ''
      }`}
      style={{ width: NODE_W, height: NODE_H }}
    >
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          {isChampion && (
            <span className="font-display text-xs italic leading-none text-brass-bright">
              ◆
            </span>
          )}
          <span className="label-cap text-[8.5px] tracking-[0.22em]">Specimen</span>
        </div>
        <span className={`numeric font-mono text-[11px] font-semibold ${tierTone}`}>
          {fitness.toFixed(2)}
        </span>
      </div>

      <div className="font-mono text-[12px] leading-tight text-bone">{genome.id}</div>

      <div className="flex items-center justify-between gap-2 font-mono text-[9.5px] text-bone-fade">
        <span>gen {genome.generation}</span>
        <span>k={genome.retrieval_genes.chunk_size}</span>
      </div>

      {/* Fitness bar */}
      <div className="bar-track h-[2px] w-full overflow-hidden">
        <div
          className="h-full transition-[width] duration-700"
          style={{
            width: `${Math.max(4, fitness * 100)}%`,
            background: barColor,
            boxShadow: `0 0 6px ${barColor}`,
          }}
        />
      </div>
    </button>
  );
}

const nodeTypes: NodeTypes = {
  genome: GenomeNode,
};

/* ──────────────────────────────────────────────────────────────────────── */

export function FamilyTree() {
  const [population, setPopulation] = useState<PopulationResponse | null>(null);
  const [lineages, setLineages] = useState<LineageResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedGenome, setSelectedGenome] = useState<GenomeSummary | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const pop = await getPopulation();
        if (!mounted) return;
        setPopulation(pop);
        const top = [...pop.genomes]
          .sort((a, b) => b.fitness.composite - a.fitness.composite)
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
    () =>
      population
        ? buildGraph(population, lineages, setSelectedGenome)
        : { nodes: [], edges: [], championIds: new Set<string>() },
    [population, lineages],
  );

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="font-mono text-xs text-oxblood">⚠ {error}</span>
      </div>
    );
  }
  if (!population) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner label="cataloging specimens…" />
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        defaultEdgeOptions={{ type: 'smoothstep' }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          size={1.2}
          color="rgba(160, 133, 80, 0.28)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>

      {/* Floating legend */}
      <div className="pointer-events-none absolute bottom-3 left-3 border border-rule bg-ink-1/85 px-3 py-2 backdrop-blur-sm">
        <div className="label-cap mb-1 tracking-[0.24em]">Vitality key</div>
        <div className="flex flex-col gap-1 font-mono text-[10px]">
          <LegendRow color="moss" label="apex ≥ 0.75" />
          <LegendRow color="ember" label="viable 0.55–0.75" />
          <LegendRow color="oxblood" label="frail < 0.55" />
          <div className="mt-1 flex items-center gap-1.5 text-bone-dim">
            <span className="font-display italic text-brass-bright">◆</span>
            <span>champion</span>
          </div>
        </div>
      </div>

      <SpecimenDossier genome={selectedGenome} onClose={() => setSelectedGenome(null)} />
    </div>
  );
}

function LegendRow({ color, label }: { color: 'moss' | 'ember' | 'oxblood'; label: string }) {
  const cls =
    color === 'moss' ? 'bg-moss' : color === 'ember' ? 'bg-ember' : 'bg-oxblood';
  return (
    <div className="flex items-center gap-2 text-bone-dim">
      <span className={`inline-block h-[2px] w-4 ${cls}`} />
      <span>{label}</span>
    </div>
  );
}
