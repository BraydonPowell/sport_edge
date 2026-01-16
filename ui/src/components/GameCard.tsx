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
      className={`relative overflow-hidden rounded-2xl transition-all duration-300 neon-panel ${
        hasEdge ? 'neon-panel--edge' : ''
      }`}
    >
      {/* Recommended Badge */}
      {hasEdge && (
        <div className="absolute top-0 right-0 bg-[#6ad7ff] text-[#050507] text-xs font-bold px-3 py-1 rounded-bl-lg">
          EDGE DETECTED
        </div>
      )}

      <div className="p-6">
        {(league || gameTime) && (
          <div className="flex justify-between text-xs neon-muted mb-3">
            <span className="uppercase tracking-wider">{league || ''}</span>
            <span>{gameTime ? new Date(gameTime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : ''}</span>
          </div>
        )}
        {/* Teams */}
        <div className="flex items-center justify-between mb-6">
          {/* Away Team */}
          <div className="flex-1 text-center">
            <div className="text-3xl font-bold mb-1">{getTeamAbbrev(awayTeam)}</div>
            <div className="text-sm neon-muted mb-2">{awayTeam}</div>
            <div className="flex items-center justify-center gap-2">
              <span className={`text-2xl font-mono font-bold ${recommendedBet === 'away' ? 'text-[#6ad7ff]' : 'text-[#f2f2f7]'}`}>
                {formatOdds(awayOdds)}
              </span>
              {recommendedBet === 'away' && (
                <span className="text-[#6ad7ff] animate-pulse-glow">*</span>
              )}
            </div>
          </div>

          {/* VS */}
          <div className="px-6">
            {showDraw ? (
              <div className="text-center">
                <div className="text-xs neon-muted mb-1">DRAW</div>
                <div className={`text-sm font-mono font-bold ${recommendedBet === 'draw' ? 'text-[#6ad7ff]' : 'text-[#f2f2f7]'}`}>
                  {drawOdds !== null ? formatOdds(drawOdds) : '--'}
                </div>
                <div className="text-xs neon-muted mt-1">
                  {drawProbability?.toFixed(1)}%
                </div>
              </div>
            ) : (
              <div className="neon-muted text-xl font-light">@</div>
            )}
          </div>

          {/* Home Team */}
          <div className="flex-1 text-center">
            <div className="text-3xl font-bold mb-1">{getTeamAbbrev(homeTeam)}</div>
            <div className="text-sm neon-muted mb-2">{homeTeam}</div>
            <div className="flex items-center justify-center gap-2">
              <span className={`text-2xl font-mono font-bold ${recommendedBet === 'home' ? 'text-[#6ad7ff]' : 'text-[#f2f2f7]'}`}>
                {formatOdds(homeOdds)}
              </span>
              {recommendedBet === 'home' && (
                <span className="text-[#6ad7ff] animate-pulse-glow">*</span>
              )}
            </div>
          </div>
        </div>

        {/* Probability Bars */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="neon-muted">Win Probability</span>
          </div>
          <div className="flex h-3 rounded-full overflow-hidden bg-[#161622]">
            <div
              className={`transition-all duration-500 ${recommendedBet === 'away' ? 'bg-[#6ad7ff]' : 'bg-[#402fb5]'}`}
              style={{ width: `${awayProbability}%` }}
            />
            {showDraw && (
              <div
                className={`transition-all duration-500 ${recommendedBet === 'draw' ? 'bg-[#6ad7ff]' : 'bg-[#7a4fe5]'}`}
                style={{ width: `${drawProbability ?? 0}%` }}
              />
            )}
            <div
              className={`transition-all duration-500 ${recommendedBet === 'home' ? 'bg-[#6ad7ff]' : 'bg-[#cf30aa]'}`}
              style={{ width: `${homeProbability}%` }}
            />
          </div>
          <div className="flex justify-between text-sm mt-2">
            <span className={recommendedBet === 'away' ? 'text-[#6ad7ff] font-semibold' : 'neon-muted'}>
              {awayProbability}%
            </span>
            {showDraw && (
              <span className={recommendedBet === 'draw' ? 'text-[#6ad7ff] font-semibold' : 'neon-muted'}>
                {drawProbability?.toFixed(1)}%
              </span>
            )}
            <span className={recommendedBet === 'home' ? 'text-[#6ad7ff] font-semibold' : 'neon-muted'}>
              {homeProbability}%
            </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Elo Ratings */}
          <div className="bg-[#07070d] rounded-xl p-4 border border-[rgba(90,86,140,0.35)]">
            <div className="text-xs neon-muted uppercase tracking-wider mb-2">Elo Rating</div>
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
          <div className="bg-[#07070d] rounded-xl p-4 border border-[rgba(90,86,140,0.35)]">
            <div className="text-xs neon-muted uppercase tracking-wider mb-2">Edge %</div>
            <div className={`grid ${showDraw ? 'grid-cols-3' : 'grid-cols-2'} gap-2`}>
              <div className={`text-lg font-mono ${awayEdge > 0 ? 'text-[#6ad7ff]' : 'text-[#ef4444]'}`}>
                {awayEdge > 0 ? '+' : ''}{awayEdge}%
              </div>
              {showDraw && (
                <div className={`text-lg font-mono text-center ${drawEdge && drawEdge > 0 ? 'text-[#6ad7ff]' : 'text-[#ef4444]'}`}>
                  {drawEdge && drawEdge > 0 ? '+' : ''}{drawEdge ?? 0}%
                </div>
              )}
              <div className={`text-lg font-mono ${homeEdge > 0 ? 'text-[#6ad7ff]' : 'text-[#ef4444]'}`}>
                {homeEdge > 0 ? '+' : ''}{homeEdge}%
              </div>
            </div>
          </div>
        </div>

        {/* Confidence + Stake */}
        {hasEdge && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-[#07070d] rounded-xl p-4 border border-[rgba(90,86,140,0.35)]">
              <div className="text-xs neon-muted uppercase tracking-wider mb-2">Confidence</div>
              <div className={`text-lg font-mono ${confidenceLabel === 'HIGH' ? 'text-[#6ad7ff]' : confidenceLabel === 'MED' ? 'text-[#f59e0b]' : 'text-[#ef4444]'}`}>
                {confidenceLabel}
              </div>
            </div>
            <div className="bg-[#07070d] rounded-xl p-4 border border-[rgba(90,86,140,0.35)]">
              <div className="text-xs neon-muted uppercase tracking-wider mb-2">Stake Guide</div>
              <div className="text-lg font-mono text-[#f2f2f7]">{stakeLabel}</div>
              <div className="text-xs neon-muted mt-1">Based on edge + EV</div>
            </div>
          </div>
        )}

        {/* Transparency */}
        {hasEdge && (
          <div className="bg-[#07070d] rounded-xl p-4 mb-6 border border-[rgba(90,86,140,0.35)]">
            <div className="text-xs neon-muted uppercase tracking-wider mb-3">Bet Breakdown</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="neon-muted">Model Prob</div>
              <div className="text-[#f2f2f7] font-mono">{betModelProb?.toFixed(1)}%</div>
              <div className="neon-muted">Market Prob</div>
              <div className="text-[#f2f2f7] font-mono">{betMarketProb?.toFixed(1)}%</div>
              <div className="neon-muted">Decimal Odds</div>
              <div className="text-[#f2f2f7] font-mono">{betDecimal?.toFixed(3)}</div>
              <div className="neon-muted">EV / $1</div>
              <div className="text-[#f2f2f7] font-mono">{betEV?.toFixed(3)}</div>
              <div className="neon-muted">Stake %</div>
              <div className="text-[#f2f2f7] font-mono">{betStakeFrac ? (betStakeFrac * 100).toFixed(2) + '%' : '0.00%'}</div>
              <div className="neon-muted">Stake $</div>
              <div className="text-[#f2f2f7] font-mono">{betStakeDollars ? `$${betStakeDollars.toFixed(2)}` : '$0.00'}</div>
            </div>
          </div>
        )}

        {/* Injuries Section */}
        {(homeInjuries.length > 0 || awayInjuries.length > 0) && (
          <div className="border-t border-[rgba(90,86,140,0.45)] pt-4 mb-4">
            <div className="text-xs neon-muted uppercase tracking-wider mb-3">Injuries</div>
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
                      <div className="text-xs neon-muted">+{awayInjuries.length - 3} more</div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs neon-muted">No injuries</div>
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
                      <div className="text-xs neon-muted">+{homeInjuries.length - 3} more</div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs neon-muted">No injuries</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Bet Recommendation */}
        {hasEdge && (
          <div className="bg-[#07070d] border border-[rgba(106,215,255,0.4)] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[#6ad7ff] font-bold text-lg">{betSide}</div>
                <div className="text-sm text-[#a1a1aa]">
                  {formatOdds(betOdds)} | Edge: +{betEdge}%
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs neon-muted uppercase">Expected Value</div>
                <div className="text-2xl font-mono text-[#6ad7ff] font-bold">
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
