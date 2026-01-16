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
    <div className="neon-panel overflow-hidden h-full flex flex-col">
      <div className="p-5 pt-4 flex flex-col flex-1">
        {/* Header: Player + Prop */}
        <div className="flex items-start gap-3 mb-4">
          {/* Rank Badge */}
          {rank && (
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#402fb5] to-[#cf30aa] flex items-center justify-center flex-shrink-0 shadow-[0_0_12px_rgba(207,48,170,0.4)]">
              <span className="text-white font-bold text-sm">#{rank}</span>
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="text-lg font-bold text-[#f2f2f7] truncate">{playerName}</div>
            <div className="text-sm neon-muted">{team} vs {opponent}</div>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-bold flex-shrink-0 ${isOver ? 'bg-[#6ad7ff]/20 text-[#6ad7ff]' : 'bg-[#ef4444]/20 text-[#ef4444]'}`}>
            {recommendedSide?.toUpperCase()}
          </div>
        </div>

        {/* Main Bet Info */}
        <div className="bg-[#07070d] rounded-xl p-4 mb-4 border border-[rgba(90,86,140,0.35)]">
          <div className="text-center mb-3">
            <div className="text-xs neon-muted uppercase tracking-wider mb-1">{formatPropType(propType)}</div>
            <div className="flex items-center justify-center gap-3">
              <span className="text-3xl font-mono font-bold text-[#f2f2f7]">{isOver ? 'O' : 'U'} {line}</span>
              <span className="text-lg neon-muted">@</span>
              <span className={`text-xl font-mono font-bold ${isOver ? 'text-[#6ad7ff]' : 'text-[#ef4444]'}`}>
                {formatOdds(odds)}
              </span>
            </div>
          </div>

          {/* Projection */}
          <div className="flex items-center justify-center gap-2 text-sm">
            <span className="neon-muted">Projected:</span>
            <span className={`font-mono font-bold ${projectedValue > line ? 'text-[#6ad7ff]' : 'text-[#ef4444]'}`}>
              {projectedValue.toFixed(1)}
            </span>
            <span className="neon-muted">|</span>
            <span className="neon-muted">Hit Rate:</span>
            <span className={`font-mono font-bold ${hitRateSeason > 50 ? 'text-[#6ad7ff]' : 'text-[#ef4444]'}`}>
              {hitRateSeason.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 bg-[#07070d] rounded-lg border border-[rgba(90,86,140,0.35)]">
            <div className="text-xs neon-muted mb-1">Edge</div>
            <div className={`text-xl font-mono font-bold ${Math.abs(edgePct) > 10 ? 'text-[#6ad7ff]' : 'text-[#f59e0b]'}`}>
              +{Math.abs(edgePct).toFixed(1)}%
            </div>
          </div>
          <div className="text-center p-3 bg-[#07070d] rounded-lg border border-[rgba(90,86,140,0.35)]">
            <div className="text-xs neon-muted mb-1">EV</div>
            <div className={`text-xl font-mono font-bold ${bestEv > 0.08 ? 'text-[#6ad7ff]' : 'text-[#f59e0b]'}`}>
              +{(bestEv * 100).toFixed(1)}%
            </div>
          </div>
          <div className="text-center p-3 bg-[#07070d] rounded-lg border border-[rgba(90,86,140,0.35)]">
            <div className="text-xs neon-muted mb-1">Confidence</div>
            <div className={`inline-block px-2 py-0.5 rounded text-xs font-bold text-black ${confBadge.bg}`}>
              {confBadge.text}
            </div>
          </div>
        </div>

        {/* Stake Guidance */}
        <div className="mt-3 text-center text-xs neon-muted">
          Stake guide: <span className="text-[#f2f2f7] font-semibold">{stakeLabel}</span> (edge + EV)
        </div>

        {/* Transparency */}
        {recommendedSide && (
          <div className="mt-4 bg-[#07070d] rounded-xl p-4 border border-[rgba(90,86,140,0.35)]">
            <div className="text-xs neon-muted uppercase tracking-wider mb-3">Bet Breakdown</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="neon-muted">Model Prob</div>
              <div className="text-[#f2f2f7] font-mono">{modelProbOver.toFixed(1)}%</div>
              <div className="neon-muted">Market Prob</div>
              <div className="text-[#f2f2f7] font-mono">{marketProbOver.toFixed(1)}%</div>
              <div className="neon-muted">Decimal Odds</div>
              <div className="text-[#f2f2f7] font-mono">{betDecimal?.toFixed(3)}</div>
              <div className="neon-muted">EV / $1</div>
              <div className="text-[#f2f2f7] font-mono">{bestEv.toFixed(3)}</div>
              <div className="neon-muted">Stake %</div>
              <div className="text-[#f2f2f7] font-mono">{betStakeFrac ? (betStakeFrac * 100).toFixed(2) + '%' : '0.00%'}</div>
              <div className="neon-muted">Stake $</div>
              <div className="text-[#f2f2f7] font-mono">{betStakeDollars ? `$${betStakeDollars.toFixed(2)}` : '$0.00'}</div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-auto pt-3 text-center text-xs neon-muted">
          <div>Based on {sampleSize} games this season</div>
          {book && <div className="mt-1 text-[#b3b0bf]">Line from: <span className="font-medium text-[#f2f2f7]">{book}</span></div>}
        </div>
      </div>
    </div>
  );
}
