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
      <div className="bg-[#12121a] border border-[#2a2a35] rounded-xl p-4">
        <div className="text-[#71717a] text-xs uppercase tracking-wider mb-1">Games Today</div>
        <div className="text-3xl font-bold text-[#f0f0f5]">{totalGames}</div>
      </div>

      <div className="bg-[#12121a] border border-[#2a2a35] rounded-xl p-4">
        <div className="text-[#71717a] text-xs uppercase tracking-wider mb-1">Edges Found</div>
        <div className="text-3xl font-bold text-green-400">{gamesWithEdge}</div>
      </div>

      <div className="bg-[#12121a] border border-[#2a2a35] rounded-xl p-4">
        <div className="text-[#71717a] text-xs uppercase tracking-wider mb-1">Avg Edge</div>
        <div className="text-3xl font-bold text-[#f0f0f5]">+{avgEdge.toFixed(1)}%</div>
      </div>

      <div className="bg-[#12121a] border border-[#2a2a35] rounded-xl p-4">
        <div className="text-[#71717a] text-xs uppercase tracking-wider mb-1">Best EV</div>
        <div className="text-3xl font-bold text-green-400">+{(bestEV * 100).toFixed(0)}%</div>
      </div>
    </div>
  );
}
