'use client';

interface PropCardProps {
  playerName: string;
  team: string;
  opponent: string;
  propType: string;
  line: number;
  overOdds: number;
  underOdds: number;
  projectedValue: number;
  hitRateSeason: number;
  hitRateLast10: number;
  hitRateLast5: number;
  modelProbOver: number;
  marketProbOver: number;
  edgePct: number;
  evOver: number;
  evUnder: number;
  decimalOver?: number;
  decimalUnder?: number;
  stakeFracOver?: number;
  stakeFracUnder?: number;
  stakeDollarsOver?: number;
  stakeDollarsUnder?: number;
  recommendedSide: 'over' | 'under' | null;
  confidence: string;
  sampleSize: number;
  vsOpponentAvg: number | null;
  trend: string;
  rank?: number;
  book?: string;
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

function formatPropType(type: string): string {
  const mapping: Record<string, string> = {
    points: 'Points',
    rebounds: 'Rebounds',
    assists: 'Assists',
    threes: '3-Pointers',
    pts_reb_ast: 'PTS+REB+AST',
    pts_reb: 'PTS+REB',
    pts_ast: 'PTS+AST',
    passing_yards: 'Pass Yards',
    passing_tds: 'Pass TDs',
    rushing_yards: 'Rush Yards',
    receiving_yards: 'Rec Yards',
    receptions: 'Receptions',
    goals: 'Goals',
    nhl_assists: 'Assists',
    shots: 'Shots',
  };
  return mapping[type] || type;
}

function getConfidenceBadge(confidence: string): { bg: string; text: string } {
  if (confidence === 'high') return { bg: 'bg-green-500', text: 'HIGH' };
  if (confidence === 'medium') return { bg: 'bg-yellow-500', text: 'MED' };
  return { bg: 'bg-gray-500', text: 'LOW' };
}

function getStakeGuidance(edge: number, ev: number): string {
  if (ev >= 0.12 && edge >= 15) return 'Large';
  if (ev >= 0.06 && edge >= 8) return 'Medium';
  return 'Small';
}

export default function PropCard({
  playerName,
  team,
  opponent,
  propType,
  line,
  overOdds,
  underOdds,
  projectedValue,
  hitRateSeason,
  modelProbOver,
  marketProbOver,
  edgePct,
  evOver,
  evUnder,
  decimalOver,
  decimalUnder,
  stakeFracOver,
  stakeFracUnder,
  stakeDollarsOver,
  stakeDollarsUnder,
  recommendedSide,
  confidence,
  sampleSize,
  rank,
  book,
}: PropCardProps) {
  const isOver = recommendedSide === 'over';
  const bestEv = isOver ? evOver : evUnder;
  const odds = isOver ? overOdds : underOdds;
  const confBadge = getConfidenceBadge(confidence);
  const stakeLabel = getStakeGuidance(Math.abs(edgePct), bestEv);
  const betDecimal = isOver ? decimalOver : decimalUnder;
  const betStakeFrac = isOver ? stakeFracOver : stakeFracUnder;
  const betStakeDollars = isOver ? stakeDollarsOver : stakeDollarsUnder;

  return (
    <div className="relative overflow-hidden rounded-xl border border-[#2a2a35] bg-[#12121a] hover:border-[#3a3a45] transition-all h-full flex flex-col">
      {/* Rank Badge */}
      {rank && (
        <div className="absolute top-3 left-3 w-8 h-8 rounded-full bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center z-10">
          <span className="text-white font-bold text-sm">#{rank}</span>
        </div>
      )}

      <div className="p-5 pt-4 flex flex-col flex-1">
        {/* Header: Player + Prop */}
        <div className="flex items-start justify-between mb-4 pl-10">
          <div className="min-w-0 flex-1">
            <div className="text-lg font-bold text-[#f0f0f5] truncate">{playerName}</div>
            <div className="text-sm text-[#71717a]">{team} vs {opponent}</div>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-bold flex-shrink-0 ml-2 ${isOver ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {recommendedSide?.toUpperCase()}
          </div>
        </div>

        {/* Main Bet Info */}
        <div className="bg-[#0a0a0f] rounded-xl p-4 mb-4">
          <div className="text-center mb-3">
            <div className="text-xs text-[#71717a] uppercase tracking-wider mb-1">{formatPropType(propType)}</div>
            <div className="flex items-center justify-center gap-3">
              <span className="text-3xl font-mono font-bold text-[#f0f0f5]">{isOver ? 'O' : 'U'} {line}</span>
              <span className="text-lg text-[#71717a]">@</span>
              <span className={`text-xl font-mono font-bold ${isOver ? 'text-green-400' : 'text-red-400'}`}>
                {formatOdds(odds)}
              </span>
            </div>
          </div>

          {/* Projection */}
          <div className="flex items-center justify-center gap-2 text-sm">
            <span className="text-[#71717a]">Projected:</span>
            <span className={`font-mono font-bold ${projectedValue > line ? 'text-green-400' : 'text-red-400'}`}>
              {projectedValue.toFixed(1)}
            </span>
            <span className="text-[#71717a]">|</span>
            <span className="text-[#71717a]">Hit Rate:</span>
            <span className={`font-mono font-bold ${hitRateSeason > 50 ? 'text-green-400' : 'text-red-400'}`}>
              {hitRateSeason.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 bg-[#0a0a0f] rounded-lg">
            <div className="text-xs text-[#71717a] mb-1">Edge</div>
            <div className={`text-xl font-mono font-bold ${Math.abs(edgePct) > 10 ? 'text-green-400' : 'text-yellow-400'}`}>
              +{Math.abs(edgePct).toFixed(1)}%
            </div>
          </div>
          <div className="text-center p-3 bg-[#0a0a0f] rounded-lg">
            <div className="text-xs text-[#71717a] mb-1">EV</div>
            <div className={`text-xl font-mono font-bold ${bestEv > 0.08 ? 'text-green-400' : 'text-yellow-400'}`}>
              +{(bestEv * 100).toFixed(1)}%
            </div>
          </div>
          <div className="text-center p-3 bg-[#0a0a0f] rounded-lg">
            <div className="text-xs text-[#71717a] mb-1">Confidence</div>
            <div className={`inline-block px-2 py-0.5 rounded text-xs font-bold text-black ${confBadge.bg}`}>
              {confBadge.text}
            </div>
          </div>
        </div>

        {/* Stake Guidance */}
        <div className="mt-3 text-center text-xs text-[#71717a]">
          Stake guide: <span className="text-[#f0f0f5] font-semibold">{stakeLabel}</span> (edge + EV)
        </div>

        {/* Transparency */}
        {recommendedSide && (
          <div className="mt-4 bg-[#0a0a0f] rounded-xl p-4">
            <div className="text-xs text-[#71717a] uppercase tracking-wider mb-3">Bet Breakdown</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="text-[#71717a]">Model Prob</div>
              <div className="text-[#f0f0f5] font-mono">{modelProbOver.toFixed(1)}%</div>
              <div className="text-[#71717a]">Market Prob</div>
              <div className="text-[#f0f0f5] font-mono">{marketProbOver.toFixed(1)}%</div>
              <div className="text-[#71717a]">Decimal Odds</div>
              <div className="text-[#f0f0f5] font-mono">{betDecimal?.toFixed(3)}</div>
              <div className="text-[#71717a]">EV / $1</div>
              <div className="text-[#f0f0f5] font-mono">{bestEv.toFixed(3)}</div>
              <div className="text-[#71717a]">Stake %</div>
              <div className="text-[#f0f0f5] font-mono">{betStakeFrac ? (betStakeFrac * 100).toFixed(2) + '%' : '0.00%'}</div>
              <div className="text-[#71717a]">Stake $</div>
              <div className="text-[#f0f0f5] font-mono">{betStakeDollars ? `$${betStakeDollars.toFixed(2)}` : '$0.00'}</div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-auto pt-3 text-center text-xs text-[#71717a]">
          <div>Based on {sampleSize} games this season</div>
          {book && <div className="mt-1 text-[#9ca3af]">Line from: <span className="font-medium text-[#f0f0f5]">{book}</span></div>}
        </div>
      </div>
    </div>
  );
}
