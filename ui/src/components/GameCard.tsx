'use client';

interface Injury {
  player: string;
  status: string;
  impact: number;
}

interface GameCardProps {
  homeTeam: string;
  awayTeam: string;
  homeElo: number;
  awayElo: number;
  homeEloAdjusted: number;
  awayEloAdjusted: number;
  homeProbability: number;
  awayProbability: number;
  drawProbability?: number | null;
  homeOdds: number;
  awayOdds: number;
  drawOdds?: number | null;
  homeMarketProb?: number;
  awayMarketProb?: number;
  drawMarketProb?: number | null;
  homeDecimalOdds?: number;
  awayDecimalOdds?: number;
  drawDecimalOdds?: number | null;
  homeEdge: number;
  awayEdge: number;
  drawEdge?: number | null;
  homeEV: number;
  awayEV: number;
  drawEV?: number | null;
  homeStakeFrac?: number;
  awayStakeFrac?: number;
  drawStakeFrac?: number | null;
  homeStakeDollars?: number;
  awayStakeDollars?: number;
  drawStakeDollars?: number | null;
  recommendedBet: 'home' | 'away' | 'draw' | null;
  league?: string;
  gameTime?: string;
  homeInjuries?: Injury[];
  awayInjuries?: Injury[];
  homeInjuryImpact?: number;
  awayInjuryImpact?: number;
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

function getTeamAbbrev(team: string): string {
  const abbrevs: Record<string, string> = {
    'Houston Rockets': 'HOU',
    'Chicago Bulls': 'CHI',
    'Los Angeles Lakers': 'LAL',
    'Atlanta Hawks': 'ATL',
    'Boston Celtics': 'BOS',
    'New York Knicks': 'NYK',
    'Miami Heat': 'MIA',
    'Golden State Warriors': 'GSW',
    'Denver Nuggets': 'DEN',
    'Phoenix Suns': 'PHX',
    'Milwaukee Bucks': 'MIL',
    'Dallas Mavericks': 'DAL',
    'Philadelphia 76ers': 'PHI',
    'Cleveland Cavaliers': 'CLE',
    'Oklahoma City Thunder': 'OKC',
    'Los Angeles Clippers': 'LAC',
  };
  return abbrevs[team] || team.slice(0, 3).toUpperCase();
}

function getConfidenceLabel(edge: number | null | undefined, ev: number | null | undefined): string {
  if (edge === null || edge === undefined || ev === null || ev === undefined) {
    return 'LOW';
  }
  if (ev >= 0.12 && edge >= 15) return 'HIGH';
  if (ev >= 0.06 && edge >= 8) return 'MED';
  return 'LOW';
}

function getStakeGuidance(edge: number | null | undefined, ev: number | null | undefined): string {
  if (edge === null || edge === undefined || ev === null || ev === undefined) {
    return 'Small';
  }
  if (ev >= 0.12 && edge >= 15) return 'Large';
  if (ev >= 0.06 && edge >= 8) return 'Medium';
  return 'Small';
}

export default function GameCard({
  homeTeam,
  awayTeam,
  homeElo,
  awayElo,
  homeEloAdjusted,
  awayEloAdjusted,
  homeProbability,
  awayProbability,
  drawProbability = null,
  homeOdds,
  awayOdds,
  drawOdds = null,
  homeMarketProb,
  awayMarketProb,
  drawMarketProb = null,
  homeDecimalOdds,
  awayDecimalOdds,
  drawDecimalOdds = null,
  homeEdge,
  awayEdge,
  drawEdge = null,
  homeEV,
  awayEV,
  drawEV = null,
  homeStakeFrac,
  awayStakeFrac,
  drawStakeFrac = null,
  homeStakeDollars,
  awayStakeDollars,
  drawStakeDollars = null,
  recommendedBet,
  league,
  gameTime,
  homeInjuries = [],
  awayInjuries = [],
  homeInjuryImpact = 0,
  awayInjuryImpact = 0,
}: GameCardProps) {
  const hasEdge = recommendedBet !== null;
  const betSide =
    recommendedBet === 'home'
      ? homeTeam
      : recommendedBet === 'away'
        ? awayTeam
        : 'Draw';
  const betOdds =
    recommendedBet === 'home'
      ? homeOdds
      : recommendedBet === 'away'
        ? awayOdds
        : drawOdds;
  const betEdge =
    recommendedBet === 'home'
      ? homeEdge
      : recommendedBet === 'away'
        ? awayEdge
        : drawEdge;
  const betEV =
    recommendedBet === 'home'
      ? homeEV
      : recommendedBet === 'away'
        ? awayEV
        : drawEV;
  const showDraw = drawOdds !== null && drawProbability !== null;
  const confidenceLabel = getConfidenceLabel(betEdge, betEV);
  const stakeLabel = getStakeGuidance(betEdge, betEV);
  const betModelProb =
    recommendedBet === 'home'
      ? homeProbability
      : recommendedBet === 'away'
        ? awayProbability
        : drawProbability;
  const betMarketProb =
    recommendedBet === 'home'
      ? homeMarketProb
      : recommendedBet === 'away'
        ? awayMarketProb
        : drawMarketProb;
  const betDecimal =
    recommendedBet === 'home'
      ? homeDecimalOdds
      : recommendedBet === 'away'
        ? awayDecimalOdds
        : drawDecimalOdds;
  const betStakeFrac =
    recommendedBet === 'home'
      ? homeStakeFrac
      : recommendedBet === 'away'
        ? awayStakeFrac
        : drawStakeFrac;
  const betStakeDollars =
    recommendedBet === 'home'
      ? homeStakeDollars
      : recommendedBet === 'away'
        ? awayStakeDollars
        : drawStakeDollars;

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border transition-all duration-300 ${
        hasEdge
          ? 'border-green-500/50 bg-gradient-to-br from-[#12121a] to-[#0d1f0d] glow-green'
          : 'border-[#2a2a35] bg-[#12121a] hover:border-[#3a3a45]'
      }`}
    >
      {/* Recommended Badge */}
      {hasEdge && (
        <div className="absolute top-0 right-0 bg-green-500 text-black text-xs font-bold px-3 py-1 rounded-bl-lg">
          EDGE DETECTED
        </div>
      )}

      <div className="p-6">
        {(league || gameTime) && (
          <div className="flex justify-between text-xs text-[#71717a] mb-3">
            <span className="uppercase tracking-wider">{league || ''}</span>
            <span>{gameTime ? new Date(gameTime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : ''}</span>
          </div>
        )}
        {/* Teams */}
        <div className="flex items-center justify-between mb-6">
          {/* Away Team */}
          <div className="flex-1 text-center">
            <div className="text-3xl font-bold mb-1">{getTeamAbbrev(awayTeam)}</div>
            <div className="text-sm text-[#71717a] mb-2">{awayTeam}</div>
            <div className="flex items-center justify-center gap-2">
              <span className={`text-2xl font-mono font-bold ${recommendedBet === 'away' ? 'text-green-400' : 'text-[#f0f0f5]'}`}>
                {formatOdds(awayOdds)}
              </span>
              {recommendedBet === 'away' && (
                <span className="text-green-400 animate-pulse-glow">*</span>
              )}
            </div>
          </div>

          {/* VS */}
          <div className="px-6">
            {showDraw ? (
              <div className="text-center">
                <div className="text-xs text-[#71717a] mb-1">DRAW</div>
                <div className={`text-sm font-mono font-bold ${recommendedBet === 'draw' ? 'text-green-400' : 'text-[#f0f0f5]'}`}>
                  {drawOdds !== null ? formatOdds(drawOdds) : '--'}
                </div>
                <div className="text-xs text-[#71717a] mt-1">
                  {drawProbability?.toFixed(1)}%
                </div>
              </div>
            ) : (
              <div className="text-[#71717a] text-xl font-light">@</div>
            )}
          </div>

          {/* Home Team */}
          <div className="flex-1 text-center">
            <div className="text-3xl font-bold mb-1">{getTeamAbbrev(homeTeam)}</div>
            <div className="text-sm text-[#71717a] mb-2">{homeTeam}</div>
            <div className="flex items-center justify-center gap-2">
              <span className={`text-2xl font-mono font-bold ${recommendedBet === 'home' ? 'text-green-400' : 'text-[#f0f0f5]'}`}>
                {formatOdds(homeOdds)}
              </span>
              {recommendedBet === 'home' && (
                <span className="text-green-400 animate-pulse-glow">*</span>
              )}
            </div>
          </div>
        </div>

        {/* Probability Bars */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-[#71717a]">Win Probability</span>
          </div>
          <div className="flex h-3 rounded-full overflow-hidden bg-[#2a2a35]">
            <div
              className={`transition-all duration-500 ${recommendedBet === 'away' ? 'bg-green-500' : 'bg-blue-500'}`}
              style={{ width: `${awayProbability}%` }}
            />
            {showDraw && (
              <div
                className={`transition-all duration-500 ${recommendedBet === 'draw' ? 'bg-green-500' : 'bg-purple-500'}`}
                style={{ width: `${drawProbability ?? 0}%` }}
              />
            )}
            <div
              className={`transition-all duration-500 ${recommendedBet === 'home' ? 'bg-green-500' : 'bg-orange-500'}`}
              style={{ width: `${homeProbability}%` }}
            />
          </div>
          <div className="flex justify-between text-sm mt-2">
            <span className={recommendedBet === 'away' ? 'text-green-400 font-semibold' : 'text-[#71717a]'}>
              {awayProbability}%
            </span>
            {showDraw && (
              <span className={recommendedBet === 'draw' ? 'text-green-400 font-semibold' : 'text-[#71717a]'}>
                {drawProbability?.toFixed(1)}%
              </span>
            )}
            <span className={recommendedBet === 'home' ? 'text-green-400 font-semibold' : 'text-[#71717a]'}>
              {homeProbability}%
            </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Elo Ratings */}
          <div className="bg-[#0a0a0f] rounded-xl p-4">
            <div className="text-xs text-[#71717a] uppercase tracking-wider mb-2">Elo Rating</div>
            <div className="flex justify-between">
              <div>
                <div className="text-lg font-mono">{awayEloAdjusted}</div>
                {awayInjuryImpact !== 0 && (
                  <div className="text-xs text-red-400">({awayInjuryImpact})</div>
                )}
              </div>
              <div className="text-right">
                <div className="text-lg font-mono">{homeEloAdjusted}</div>
                {homeInjuryImpact !== 0 && (
                  <div className="text-xs text-red-400">({homeInjuryImpact})</div>
                )}
              </div>
            </div>
          </div>

          {/* Edge */}
          <div className="bg-[#0a0a0f] rounded-xl p-4">
            <div className="text-xs text-[#71717a] uppercase tracking-wider mb-2">Edge %</div>
            <div className={`grid ${showDraw ? 'grid-cols-3' : 'grid-cols-2'} gap-2`}>
              <div className={`text-lg font-mono ${awayEdge > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {awayEdge > 0 ? '+' : ''}{awayEdge}%
              </div>
              {showDraw && (
                <div className={`text-lg font-mono text-center ${drawEdge && drawEdge > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {drawEdge && drawEdge > 0 ? '+' : ''}{drawEdge ?? 0}%
                </div>
              )}
              <div className={`text-lg font-mono ${homeEdge > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {homeEdge > 0 ? '+' : ''}{homeEdge}%
              </div>
            </div>
          </div>
        </div>

        {/* Confidence + Stake */}
        {hasEdge && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-[#0a0a0f] rounded-xl p-4">
              <div className="text-xs text-[#71717a] uppercase tracking-wider mb-2">Confidence</div>
              <div className={`text-lg font-mono ${confidenceLabel === 'HIGH' ? 'text-green-400' : confidenceLabel === 'MED' ? 'text-yellow-400' : 'text-red-400'}`}>
                {confidenceLabel}
              </div>
            </div>
            <div className="bg-[#0a0a0f] rounded-xl p-4">
              <div className="text-xs text-[#71717a] uppercase tracking-wider mb-2">Stake Guide</div>
              <div className="text-lg font-mono text-[#f0f0f5]">{stakeLabel}</div>
              <div className="text-xs text-[#71717a] mt-1">Based on edge + EV</div>
            </div>
          </div>
        )}

        {/* Transparency */}
        {hasEdge && (
          <div className="bg-[#0a0a0f] rounded-xl p-4 mb-6">
            <div className="text-xs text-[#71717a] uppercase tracking-wider mb-3">Bet Breakdown</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="text-[#71717a]">Model Prob</div>
              <div className="text-[#f0f0f5] font-mono">{betModelProb?.toFixed(1)}%</div>
              <div className="text-[#71717a]">Market Prob</div>
              <div className="text-[#f0f0f5] font-mono">{betMarketProb?.toFixed(1)}%</div>
              <div className="text-[#71717a]">Decimal Odds</div>
              <div className="text-[#f0f0f5] font-mono">{betDecimal?.toFixed(3)}</div>
              <div className="text-[#71717a]">EV / $1</div>
              <div className="text-[#f0f0f5] font-mono">{betEV?.toFixed(3)}</div>
              <div className="text-[#71717a]">Stake %</div>
              <div className="text-[#f0f0f5] font-mono">{betStakeFrac ? (betStakeFrac * 100).toFixed(2) + '%' : '0.00%'}</div>
              <div className="text-[#71717a]">Stake $</div>
              <div className="text-[#f0f0f5] font-mono">{betStakeDollars ? `$${betStakeDollars.toFixed(2)}` : '$0.00'}</div>
            </div>
          </div>
        )}

        {/* Injuries Section */}
        {(homeInjuries.length > 0 || awayInjuries.length > 0) && (
          <div className="border-t border-[#2a2a35] pt-4 mb-4">
            <div className="text-xs text-[#71717a] uppercase tracking-wider mb-3">Injuries</div>
            <div className="grid grid-cols-2 gap-4">
              {/* Away Injuries */}
              <div>
                {awayInjuries.length > 0 ? (
                  <div className="space-y-1">
                    {awayInjuries.slice(0, 3).map((inj, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <span className={`w-2 h-2 rounded-full ${inj.status === 'Out' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                        <span className="text-[#a1a1aa] truncate">{inj.player}</span>
                      </div>
                    ))}
                    {awayInjuries.length > 3 && (
                      <div className="text-xs text-[#71717a]">+{awayInjuries.length - 3} more</div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-[#71717a]">No injuries</div>
                )}
              </div>

              {/* Home Injuries */}
              <div>
                {homeInjuries.length > 0 ? (
                  <div className="space-y-1">
                    {homeInjuries.slice(0, 3).map((inj, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <span className={`w-2 h-2 rounded-full ${inj.status === 'Out' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                        <span className="text-[#a1a1aa] truncate">{inj.player}</span>
                      </div>
                    ))}
                    {homeInjuries.length > 3 && (
                      <div className="text-xs text-[#71717a]">+{homeInjuries.length - 3} more</div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-[#71717a]">No injuries</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Bet Recommendation */}
        {hasEdge && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-green-400 font-bold text-lg">{betSide}</div>
                <div className="text-sm text-[#a1a1aa]">
                  {formatOdds(betOdds)} | Edge: +{betEdge}%
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-[#71717a] uppercase">Expected Value</div>
                <div className="text-2xl font-mono text-green-400 font-bold">
                  +{(betEV * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
