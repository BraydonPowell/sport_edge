'use client';

interface StatsBarProps {
  totalGames: number;
  gamesWithEdge: number;
  avgEdge: number;
  bestEV: number;
}

export default function StatsBar({ totalGames, gamesWithEdge, avgEdge, bestEV }: StatsBarProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div className="neon-panel p-4">
        <div className="neon-muted text-xs uppercase tracking-wider mb-1">Games Today</div>
        <div className="text-3xl font-bold text-[#f2f2f7]">{totalGames}</div>
      </div>

      <div className="neon-panel p-4">
        <div className="neon-muted text-xs uppercase tracking-wider mb-1">Edges Found</div>
        <div className="text-3xl font-bold text-[#6ad7ff]">{gamesWithEdge}</div>
      </div>

      <div className="neon-panel p-4">
        <div className="neon-muted text-xs uppercase tracking-wider mb-1">Avg Edge</div>
        <div className="text-3xl font-bold text-[#f2f2f7]">+{avgEdge.toFixed(1)}%</div>
      </div>

      <div className="neon-panel p-4">
        <div className="neon-muted text-xs uppercase tracking-wider mb-1">Best EV</div>
        <div className="text-3xl font-bold text-[#cf30aa]">+{(bestEV * 100).toFixed(0)}%</div>
      </div>
    </div>
  );
}
