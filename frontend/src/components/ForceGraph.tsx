'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import * as d3 from 'd3';
import type { GraphData, GraphNode, GraphLink } from '@/types';

interface Props {
  data: GraphData;
  width?: number;
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
}

const NODE_COLORS: Record<string, string> = {
  user: '#f59e0b',
  movie: '#60a5fa',
  genre: '#34d399',
  keyword: '#a78bfa',
  mood: '#f472b6',
  archetype: '#fb923c',
};

const NODE_SIZES: Record<string, number> = {
  user: 28,
  movie: 20,
  genre: 14,
  keyword: 10,
  mood: 12,
  archetype: 16,
};

export default function ForceGraph({ data, width = 900, height = 600, onNodeClick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const renderGraph = useCallback(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const g = svg.append('g');

    // Zoom
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Tooltip
    const tooltip = d3.select(tooltipRef.current);

    // Force simulation
    const simulation = d3.forceSimulation<GraphNode>(data.nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(data.links)
        .id((d) => d.id)
        .distance((d) => 80 / (d.weight || 1))
        .strength((d) => Math.min(d.weight * 0.15, 0.5))
      )
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d: any) => (NODE_SIZES[d.type] || 10) + 5))
      .force('x', d3.forceX(width / 2).strength(0.05))
      .force('y', d3.forceY(height / 2).strength(0.05));

    // Defs for glow + gradient background
    const defs = svg.append('defs');

    // Radial gradient for background
    const bgGrad = defs.append('radialGradient')
      .attr('id', 'bg-glow')
      .attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
    bgGrad.append('stop').attr('offset', '0%').attr('stop-color', '#f59e0b').attr('stop-opacity', '0.03');
    bgGrad.append('stop').attr('offset', '100%').attr('stop-color', '#06080f').attr('stop-opacity', '0');

    g.append('rect').attr('width', width).attr('height', height).attr('fill', 'url(#bg-glow)');

    // Node glow filters
    Object.entries(NODE_COLORS).forEach(([type, color]) => {
      const filter = defs.append('filter').attr('id', `glow-${type}`)
        .attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
      filter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
      filter.append('feFlood').attr('flood-color', color).attr('flood-opacity', '0.35').attr('result', 'color');
      filter.append('feComposite').attr('in', 'color').attr('in2', 'blur').attr('operator', 'in').attr('result', 'glow');
      const merge = filter.append('feMerge');
      merge.append('feMergeNode').attr('in', 'glow');
      merge.append('feMergeNode').attr('in', 'SourceGraphic');
    });

    // Links
    const link = g.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', '#1e293b')
      .attr('stroke-opacity', 0.5)
      .attr('stroke-width', (d) => Math.max(0.5, d.weight * 0.7));

    // Link labels
    const linkLabel = g.append('g')
      .selectAll('text')
      .data(data.links.filter(l => l.relation !== 'trata_de'))
      .join('text')
      .attr('fill', '#475569')
      .attr('font-size', '7px')
      .attr('text-anchor', 'middle')
      .text((d) => d.relation);

    // Node groups
    const node = g.append('g')
      .selectAll<SVGGElement, GraphNode>('g')
      .data(data.nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag<SVGGElement, GraphNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );

    // Node circles - outer ring
    node.append('circle')
      .attr('r', (d) => (NODE_SIZES[d.type] || 10) + 2)
      .attr('fill', 'none')
      .attr('stroke', (d) => NODE_COLORS[d.type] || '#64748b')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.2);

    // Node circles - main
    node.append('circle')
      .attr('r', (d) => NODE_SIZES[d.type] || 10)
      .attr('fill', (d) => {
        const color = NODE_COLORS[d.type] || '#64748b';
        return color + '18'; // very low opacity fill
      })
      .attr('stroke', (d) => NODE_COLORS[d.type] || '#64748b')
      .attr('stroke-width', 1.5)
      .attr('filter', (d) => `url(#glow-${d.type})`);

    // Node icons/labels
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => NODE_SIZES[d.type] + 14)
      .attr('fill', '#94a3b8')
      .attr('font-size', (d) => d.type === 'user' ? '11px' : d.type === 'movie' ? '10px' : '8px')
      .attr('font-weight', (d) => d.type === 'movie' || d.type === 'user' ? '600' : '400')
      .text((d) => {
        if (d.label.length > 20) return d.label.slice(0, 18) + '…';
        return d.label;
      });

    // Type icon inside node
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', (d) => `${Math.max(NODE_SIZES[d.type] * 0.6, 7)}px`)
      .text((d) => {
        switch (d.type) {
          case 'user': return '👤';
          case 'movie': return '🎬';
          case 'genre': return '🏷';
          case 'keyword': return '🔑';
          case 'mood': return '💫';
          case 'archetype': return '⭐';
          default: return '';
        }
      });

    // Hover interactions
    node
      .on('mouseover', (event, d) => {
        tooltip
          .style('opacity', 1)
          .style('left', `${event.pageX + 12}px`)
          .style('top', `${event.pageY - 12}px`)
          .html(getTooltipContent(d));

        const connectedIds = new Set<string>();
        data.links.forEach((l) => {
          const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
          const targetId = typeof l.target === 'string' ? l.target : l.target.id;
          if (sourceId === d.id) connectedIds.add(targetId);
          if (targetId === d.id) connectedIds.add(sourceId);
        });
        connectedIds.add(d.id);

        node.style('opacity', (n) => connectedIds.has(n.id) ? 1 : 0.15);
        link.style('opacity', (l) => {
          const sid = typeof l.source === 'string' ? l.source : (l.source as GraphNode).id;
          const tid = typeof l.target === 'string' ? l.target : (l.target as GraphNode).id;
          return sid === d.id || tid === d.id ? 0.9 : 0.03;
        }).style('stroke', (l) => {
          const sid = typeof l.source === 'string' ? l.source : (l.source as GraphNode).id;
          const tid = typeof l.target === 'string' ? l.target : (l.target as GraphNode).id;
          return (sid === d.id || tid === d.id) ? NODE_COLORS[d.type] : '#1e293b';
        });
      })
      .on('mouseout', () => {
        tooltip.style('opacity', 0);
        node.style('opacity', 1);
        link.style('opacity', 0.5).style('stroke', '#1e293b');
      })
      .on('click', (_, d) => {
        setSelectedNode(d.id);
        onNodeClick?.(d);
      });

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      linkLabel
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    // Initial zoom to fit
    setTimeout(() => {
      svg.call(zoom.transform, d3.zoomIdentity.translate(0, 0).scale(0.85));
    }, 500);

    return () => {
      simulation.stop();
    };
  }, [data, width, height, onNodeClick]);

  useEffect(() => {
    renderGraph();
  }, [renderGraph]);

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="rounded-xl border border-white/[0.06]"
        style={{ background: '#06080f', minHeight: '400px' }}
      />
      <div
        ref={tooltipRef}
        className="graph-tooltip"
        style={{ opacity: 0 }}
      />
      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-1.5 text-[10px]">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5 glass-card px-2 py-1 rounded-md">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}60` }} />
            <span className="text-cinema-textMuted capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function getTooltipContent(node: GraphNode): string {
  const color = NODE_COLORS[node.type] || '#94a3b8';
  let html = `<div style="font-weight:600;color:${color};font-size:13px">${node.label}</div>`;
  html += `<div style="color:#64748b;font-size:10px;margin-top:2px;text-transform:uppercase;letter-spacing:0.05em">${node.type}</div>`;

  if (node.type === 'movie') {
    if (node.year) html += `<div style="margin-top:4px;color:#94a3b8">📅 ${node.year}</div>`;
    if (node.score) html += `<div style="color:#fbbf24">⭐ ${node.score}/10</div>`;
    if (node.reason) html += `<div style="margin-top:4px;font-style:italic;color:#a78bfa;font-size:11px">${node.reason}</div>`;
  }

  if (node.type === 'user' && node.tags) {
    html += `<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:3px">${node.tags.map(t =>
      `<span style="background:rgba(245,158,11,0.12);color:#fbbf24;padding:2px 6px;border-radius:4px;font-size:9px;border:1px solid rgba(245,158,11,0.2)">${t}</span>`
    ).join('')}</div>`;
  }

  if (node.score && node.type !== 'movie') {
    html += `<div style="color:#94a3b8;margin-top:2px">Afinidad: ${node.score}</div>`;
  }

  return html;
}
