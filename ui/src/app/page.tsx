'use client';

import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import GameCard from '@/components/GameCard';
import StatsBar from '@/components/StatsBar';
import PropCard from '@/components/PropCard';

interface Injury {
  player: string;
  status: string;
  impact: number;
}

interface Prediction {
  id: string;
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
  league: string;
  gameTime?: string;
  homeInjuries?: Injury[];
  awayInjuries?: Injury[];
  homeInjuryImpact?: number;
  awayInjuryImpact?: number;
  book?: string;
}

interface PropEdge {
  player_id: string;
  player_name: string;
  team: string;
  opponent: string;
  game_date: string;
  prop_type: string;
  line: number;
  over_odds: number;
  under_odds: number;
  book: string;
  projected_value: number;
  hit_rate_season: number;
  hit_rate_last10: number;
  hit_rate_last5: number;
  model_prob_over: number;
  market_prob_over: number;
  edge_pct: number;
  ev_over: number;
  ev_under: number;
  decimal_over?: number;
  decimal_under?: number;
  stake_frac_over?: number;
  stake_frac_under?: number;
  stake_dollars_over?: number;
  stake_dollars_under?: number;
  recommended_side: 'over' | 'under' | null;
  confidence: string;
  sample_size: number;
  vs_opponent_avg: number | null;
  trend: string;
}

type ViewType = 'games' | 'props' | 'cash';
type LeagueType = 'NBA';

export default function Home() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [props, setProps] = useState<PropEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [propsLoading, setPropsLoading] = useState(false);
  const [view, setView] = useState<ViewType>('games');
  const [propsLeague, setPropsLeague] = useState<LeagueType>('NBA');
  const [propsError, setPropsError] = useState<string | null>(null);
  const [predictionsError, setPredictionsError] = useState<string | null>(null);
  const [bankroll, setBankroll] = useState(1000);
  const [propsMeta, setPropsMeta] = useState<{ events_with_props: number; events_today: number; props_count: number } | null>(null);

  useEffect(() => {
    fetchPredictions();
  }, []);

  useEffect(() => {
    if (view === 'props') {
      fetchProps(propsLeague);
    }
  }, [view, propsLeague]);

  async function fetchPredictions() {
    setPredictionsError(null);
    try {
      const res = await fetch(`/api/predictions?bankroll=${bankroll}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setPredictions(data);
      } else {
        setPredictions(data.games || []);
        setPredictionsError(data.error || null);
      }
    } catch (error) {
      console.error('Failed to fetch predictions:', error);
      setPredictionsError('Failed to load game lines.');
    } finally {
      setLoading(false);
    }
  }

  async function fetchProps(league: LeagueType) {
    setPropsLoading(true);
    setPropsError(null);
    try {
      const res = await fetch(`/api/props?league=${league}&bankroll=${bankroll}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setProps(data);
        setPropsMeta(null);
      } else {
        setProps(data.props || []);
        setPropsError(data.error || null);
        setPropsMeta(data.meta || null);
      }
    } catch (error) {
      console.error('Failed to fetch props:', error);
      setPropsError('Failed to load props data.');
      setPropsMeta(null);
    } finally {
      setPropsLoading(false);
    }
  }

  const filteredPredictions = predictions;

  // Sort props by EV and only show top 5 with edges
  const topProps = props
    .filter((p) => p.recommended_side !== null)
    .sort((a, b) => {
      const aScore = Math.max(
        a.ev_over * (a.stake_frac_over || 0),
        a.ev_under * (a.stake_frac_under || 0)
      );
      const bScore = Math.max(
        b.ev_over * (b.stake_frac_over || 0),
        b.ev_under * (b.stake_frac_under || 0)
      );
      return bScore - aScore;
    })
    .slice(0, 10);

  const gamesWithEdge = predictions.filter((p) => p.recommendedBet !== null).length;

  const edgePredictions = predictions.filter((p) => p.recommendedBet !== null);
  const avgEdge =
    edgePredictions.length > 0
      ? edgePredictions.reduce((sum, p) => {
          const edge =
            p.recommendedBet === 'home'
              ? p.homeEdge
              : p.recommendedBet === 'away'
                ? p.awayEdge
                : p.drawEdge ?? 0;
          return sum + edge;
        }, 0) / edgePredictions.length
      : 0;
  const bestEV =
    edgePredictions.length > 0
      ? Math.max(
          ...edgePredictions.map((p) =>
            p.recommendedBet === 'home'
              ? p.homeEV
              : p.recommendedBet === 'away'
                ? p.awayEV
                : p.drawEV ?? 0
          )
        )
      : 0;

  const bankrollAllocation = edgePredictions.map((p) => {
    const stake =
      p.recommendedBet === 'home'
        ? p.homeStakeDollars
        : p.recommendedBet === 'away'
          ? p.awayStakeDollars
          : p.drawStakeDollars;
    const stakeFrac =
      p.recommendedBet === 'home'
        ? p.homeStakeFrac
        : p.recommendedBet === 'away'
          ? p.awayStakeFrac
          : p.drawStakeFrac;
    return {
      id: p.id,
      league: p.league,
      label: `${p.awayTeam} @ ${p.homeTeam}`,
      side: p.recommendedBet,
      stake: stake ?? 0,
      stakeFrac: stakeFrac ?? 0,
    };
  });

  const totalStake = bankrollAllocation.reduce((sum, bet) => sum + bet.stake, 0);
  const totalStakePct = bankroll > 0 ? (totalStake / bankroll) * 100 : 0;

  const propsAllocation = topProps.map((p) => {
    const stake =
      p.recommended_side === 'over' ? p.stake_dollars_over : p.stake_dollars_under;
    const stakeFrac =
      p.recommended_side === 'over' ? p.stake_frac_over : p.stake_frac_under;
    return {
      id: `${p.player_id}-${p.prop_type}-${p.line}-${p.over_odds}-${p.under_odds}`,
      label: `${p.player_name} ${p.prop_type}`,
      side: p.recommended_side,
      stake: stake ?? 0,
      stakeFrac: stakeFrac ?? 0,
    };
  });

  const totalPropsStake = propsAllocation.reduce((sum, bet) => sum + bet.stake, 0);
  const totalPropsStakePct = bankroll > 0 ? (totalPropsStake / bankroll) * 100 : 0;

  // CASH section - Top 5 best bets across games and props with optimal allocation
  const allBets = [
    ...edgePredictions.map((p) => {
      const ev = p.recommendedBet === 'home' ? p.homeEV : p.recommendedBet === 'away' ? p.awayEV : (p.drawEV ?? 0);
      const edge = p.recommendedBet === 'home' ? p.homeEdge : p.recommendedBet === 'away' ? p.awayEdge : (p.drawEdge ?? 0);
      const odds = p.recommendedBet === 'home' ? p.homeOdds : p.recommendedBet === 'away' ? p.awayOdds : (p.drawOdds ?? 0);
      const stakeFrac = p.recommendedBet === 'home' ? p.homeStakeFrac : p.recommendedBet === 'away' ? p.awayStakeFrac : (p.drawStakeFrac ?? 0);
      return {
        id: p.id,
        type: 'game' as const,
        label: `${p.awayTeam} @ ${p.homeTeam}`,
        pick: p.recommendedBet === 'home' ? p.homeTeam : p.recommendedBet === 'away' ? p.awayTeam : 'Draw',
        side: p.recommendedBet,
        league: p.league,
        ev,
        edge,
        odds,
        book: p.book,
        stakeFrac: stakeFrac ?? 0,
        confidence: ev > 0.2 ? 'high' : ev > 0.1 ? 'medium' : 'low',
      };
    }),
    ...topProps.map((p) => {
      const ev = p.recommended_side === 'over' ? p.ev_over : p.ev_under;
      const edge = Math.abs(p.edge_pct);
      const odds = p.recommended_side === 'over' ? p.over_odds : p.under_odds;
      const stakeFrac = p.recommended_side === 'over' ? p.stake_frac_over : p.stake_frac_under;
      return {
        id: `prop-${p.player_id}-${p.prop_type}-${p.line}-${p.over_odds}`,
        type: 'prop' as const,
        label: `${p.player_name} ${p.prop_type.replace('_', ' ')}`,
        pick: `${p.recommended_side?.toUpperCase()} ${p.line}`,
        side: p.recommended_side,
        league: 'NBA',
        ev,
        edge,
        odds,
        book: p.book,
        stakeFrac: stakeFrac ?? 0,
        confidence: p.confidence,
      };
    }),
  ];

  // Sort by EV * stakeFrac (expected profit) and take top 5
  const cashBets = allBets
    .filter((b) => b.ev > 0 && b.stakeFrac > 0)
    .sort((a, b) => (b.ev * b.stakeFrac) - (a.ev * a.stakeFrac))
    .slice(0, 5);

  // Calculate optimal allocation for CASH bets (proportional to Kelly stakes)
  const totalCashKelly = cashBets.reduce((sum, b) => sum + b.stakeFrac, 0);
  const cashAllocation = cashBets.map((bet) => {
    const proportion = totalCashKelly > 0 ? bet.stakeFrac / totalCashKelly : 0;
    const allocatedAmount = proportion * bankroll;
    return {
      ...bet,
      allocatedAmount,
      allocatedPct: proportion * 100,
    };
  });
  const totalCashAmount = cashAllocation.reduce((sum, b) => sum + b.allocatedAmount, 0);

  // PARLAY Section - Best odds parlay
  // Helper to convert American odds to decimal
  const toDecimal = (american: number) => {
    if (american > 0) return 1 + american / 100;
    return 1 + 100 / Math.abs(american);
  };

  // Get all positive EV bets for parlay consideration
  const parlayEligible = allBets.filter((b) =>
    b.ev > 0
    && b.stakeFrac > 0
    && (b.book ?? '').toLowerCase() === 'fanduel'
  );

  // Calculate parlay EV: product of decimal odds * product of win probs - 1
  const calcParlayStats = (legs: typeof parlayEligible) => {
    if (legs.length === 0) return { decimalOdds: 0, americanOdds: 0, winProb: 0, ev: 0 };
    const decimalOdds = legs.reduce((acc, leg) => acc * toDecimal(leg.odds), 1);
    // Win probability = product of model probabilities (approximated from EV and odds)
    // Model prob = (1 + EV) / decimal_odds for the recommended side
    const winProb = legs.reduce((acc, leg) => {
      const decimal = toDecimal(leg.odds);
      const modelProb = (1 + leg.ev) / decimal;
      return acc * Math.min(modelProb, 0.95); // Cap at 95% to be conservative
    }, 1);
    const ev = decimalOdds * winProb - 1;
    const americanOdds = decimalOdds >= 2 ? Math.round((decimalOdds - 1) * 100) : Math.round(-100 / (decimalOdds - 1));
    return { decimalOdds, americanOdds, winProb, ev };
  };

  // Best Odds to Hit Parlay: Sort by win probability (higher = safer)
  const bestOddsCandidates = [...parlayEligible]
    .sort((a, b) => {
      const probA = (1 + a.ev) / toDecimal(a.odds);
      const probB = (1 + b.ev) / toDecimal(b.odds);
      return probB - probA; // Higher probability first
    })
    .slice(0, 3);
  const bestOddsTwoLegs = bestOddsCandidates.slice(0, 2);
  const bestOddsThreeLegs = bestOddsCandidates.slice(0, 3);
  const bestOddsTwoStats = calcParlayStats(bestOddsTwoLegs);
  const bestOddsThreeStats = calcParlayStats(bestOddsThreeLegs);
  const useTwoLegs = bestOddsTwoLegs.length === 2
    && bestOddsThreeLegs.length === 3
    && (bestOddsTwoStats.winProb - bestOddsThreeStats.winProb) >= 0.1;
  const bestOddsLegs = useTwoLegs ? bestOddsTwoLegs : bestOddsThreeLegs;
  const bestOddsParlay = useTwoLegs ? bestOddsTwoStats : bestOddsThreeStats;

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <Header />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* View Toggle */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setView('games')}
            className={`px-6 py-3 rounded-xl text-sm font-semibold transition-all ${
              view === 'games'
                ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white'
                : 'bg-[#12121a] text-[#71717a] hover:text-[#f0f0f5] border border-[#2a2a35]'
            }`}
          >
            Game Lines
          </button>
          <button
            onClick={() => setView('props')}
            className={`px-6 py-3 rounded-xl text-sm font-semibold transition-all ${
              view === 'props'
                ? 'bg-gradient-to-r from-orange-500 to-pink-500 text-white'
                : 'bg-[#12121a] text-[#71717a] hover:text-[#f0f0f5] border border-[#2a2a35]'
            }`}
          >
            Player Props
          </button>
          <button
            onClick={() => setView('cash')}
            className={`px-6 py-3 rounded-xl text-sm font-semibold transition-all ${
              view === 'cash'
                ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white'
                : 'bg-[#12121a] text-[#71717a] hover:text-[#f0f0f5] border border-[#2a2a35]'
            }`}
          >
            Cash
          </button>
        </div>

        <div className="max-w-xl mx-auto mb-8">
          <div className="bg-[#12121a] border border-[#2a2a35] rounded-xl p-4 flex flex-col sm:flex-row items-center gap-4">
            <div className="text-sm text-[#71717a] uppercase tracking-wider">Tonight's Bankroll</div>
            <div className="flex items-center gap-2">
              <span className="text-[#71717a]">$</span>
              <input
                type="number"
                min="0"
                step="50"
                value={bankroll}
                onChange={(event) => setBankroll(Number(event.target.value || 0))}
                onBlur={() => {
                  fetchPredictions();
                  if (view === 'props') fetchProps(propsLeague);
                }}
                className="w-32 bg-[#0a0a0f] border border-[#2a2a35] rounded-lg px-3 py-2 text-[#f0f0f5] font-mono"
              />
            </div>
            <div className="text-xs text-[#71717a]">Stake sizing updates on blur</div>
          </div>
        </div>

        {view === 'games' && (
          <>
            {/* Stats */}
            <StatsBar
              totalGames={predictions.length}
              gamesWithEdge={gamesWithEdge}
              avgEdge={avgEdge}
              bestEV={bestEV}
            />

            <div className="flex justify-end mb-4">
              <button
                onClick={() => fetchPredictions()}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-[#12121a] text-[#71717a] hover:text-[#f0f0f5] border border-[#2a2a35]"
              >
                Refresh Games
              </button>
            </div>

            {bankrollAllocation.length > 0 && (
              <div className="bg-[#12121a] border border-[#2a2a35] rounded-xl p-5 mb-8">
                <div className="flex justify-between items-center mb-4">
                  <div className="text-xs text-[#71717a] uppercase tracking-wider">Kelly-Optimized Stakes</div>
                  <div className="text-xs text-[#71717a]">Total Risk: <span className="text-[#f0f0f5] font-mono">${totalStake.toFixed(2)}</span> ({totalStakePct.toFixed(1)}%)</div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  {bankrollAllocation.map((bet) => (
                    <div key={bet.id} className="flex items-center justify-between bg-[#0a0a0f] rounded-lg px-4 py-3">
                      <div>
                        <div className="text-[#f0f0f5] font-semibold">{bet.label}</div>
                        <div className="text-[#71717a] text-xs">{bet.league} • {String(bet.side).toUpperCase()}</div>
                      </div>
                      <div className="text-right font-mono">
                        <div className="text-[#f0f0f5]">${bet.stake.toFixed(2)}</div>
                        <div className="text-[#71717a] text-xs">{(bet.stakeFrac * 100).toFixed(2)}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Games Grid */}
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-green-500/30 border-t-green-500 rounded-full animate-spin" />
                  <p className="text-[#71717a]">Loading predictions...</p>
                </div>
              </div>
            ) : predictionsError ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="text-6xl mb-4">⚠️</div>
                  <p className="text-[#f0f0f5] font-semibold mb-2">Game lines unavailable</p>
                  <p className="text-[#71717a] text-sm">{predictionsError}</p>
                </div>
              </div>
            ) : filteredPredictions.length === 0 ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="text-6xl mb-4">🎯</div>
                  <p className="text-[#71717a]">No games found today</p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {filteredPredictions.map((prediction) => (
                  <GameCard
                    key={prediction.id}
                    homeTeam={prediction.homeTeam}
                    awayTeam={prediction.awayTeam}
                    homeElo={prediction.homeElo}
                    awayElo={prediction.awayElo}
                    homeEloAdjusted={prediction.homeEloAdjusted}
                    awayEloAdjusted={prediction.awayEloAdjusted}
                    homeProbability={prediction.homeProbability}
                    awayProbability={prediction.awayProbability}
                    drawProbability={prediction.drawProbability}
                    homeOdds={prediction.homeOdds}
                    awayOdds={prediction.awayOdds}
                    drawOdds={prediction.drawOdds}
                    homeMarketProb={prediction.homeMarketProb}
                    awayMarketProb={prediction.awayMarketProb}
                    drawMarketProb={prediction.drawMarketProb}
                    homeDecimalOdds={prediction.homeDecimalOdds}
                    awayDecimalOdds={prediction.awayDecimalOdds}
                    drawDecimalOdds={prediction.drawDecimalOdds}
                    homeEdge={prediction.homeEdge}
                    awayEdge={prediction.awayEdge}
                    drawEdge={prediction.drawEdge}
                    homeEV={prediction.homeEV}
                    awayEV={prediction.awayEV}
                    drawEV={prediction.drawEV}
                    homeStakeFrac={prediction.homeStakeFrac}
                    awayStakeFrac={prediction.awayStakeFrac}
                    drawStakeFrac={prediction.drawStakeFrac}
                    homeStakeDollars={prediction.homeStakeDollars}
                    awayStakeDollars={prediction.awayStakeDollars}
                    drawStakeDollars={prediction.drawStakeDollars}
                    recommendedBet={prediction.recommendedBet}
                    league={prediction.league}
                    gameTime={prediction.gameTime}
                    homeInjuries={prediction.homeInjuries}
                    awayInjuries={prediction.awayInjuries}
                    homeInjuryImpact={prediction.homeInjuryImpact}
                    awayInjuryImpact={prediction.awayInjuryImpact}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {view === 'props' && (
          <>
            {/* League Selector */}
            <div className="flex flex-wrap gap-2 mb-4">
              {(['NBA'] as LeagueType[]).map((league) => (
                <button
                  key={league}
                  onClick={() => setPropsLeague(league)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    propsLeague === league
                      ? 'bg-orange-500 text-white'
                      : 'bg-[#12121a] text-[#71717a] hover:text-[#f0f0f5] border border-[#2a2a35]'
                  }`}
                >
                  {league}
                </button>
              ))}
            </div>

            <div className="flex justify-end mb-4">
              <button
                onClick={() => fetchProps(propsLeague)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-[#12121a] text-[#71717a] hover:text-[#f0f0f5] border border-[#2a2a35]"
              >
                Refresh Props
              </button>
            </div>

            {/* Top 5 Props */}
            <h2 className="text-xl font-bold text-[#f0f0f5] mb-4">Top 10 Best Bets</h2>
            {propsMeta && (
              <div className="mb-4 text-xs text-[#71717a]">
                Props available for {propsMeta.events_with_props} of {propsMeta.events_today} games tonight ({propsMeta.props_count} props).
                Some games may not have lines posted yet.
              </div>
            )}
            {propsLoading ? (
              <div className="flex items-center justify-center py-20">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                  <p className="text-[#71717a]">Loading {propsLeague} props...</p>
                </div>
              </div>
            ) : propsError ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="text-6xl mb-4">⚠️</div>
                  <p className="text-[#f0f0f5] font-semibold mb-2">Player props unavailable</p>
                  <p className="text-[#71717a] text-sm">{propsError}</p>
                </div>
              </div>
            ) : topProps.length === 0 ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="text-6xl mb-4">🎯</div>
                  <p className="text-[#71717a]">No edges found for {propsLeague}</p>
                </div>
              </div>
            ) : (
              <>
                {propsAllocation.length > 0 && (
                  <div className="bg-[#12121a] border border-[#2a2a35] rounded-xl p-5 mb-8">
                    <div className="flex justify-between items-center mb-4">
                      <div className="text-xs text-[#71717a] uppercase tracking-wider">Kelly-Optimized Stakes</div>
                      <div className="text-xs text-[#71717a]">Total Risk: <span className="text-[#f0f0f5] font-mono">${totalPropsStake.toFixed(2)}</span> ({totalPropsStakePct.toFixed(1)}%)</div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      {propsAllocation.map((bet, idx) => (
                        <div key={`${bet.id}-${idx}`} className="flex items-center justify-between bg-[#0a0a0f] rounded-lg px-4 py-3">
                          <div>
                            <div className="text-[#f0f0f5] font-semibold">{bet.label}</div>
                            <div className="text-[#71717a] text-xs">{String(bet.side).toUpperCase()}</div>
                          </div>
                          <div className="text-right font-mono">
                            <div className="text-[#f0f0f5]">${bet.stake.toFixed(2)}</div>
                            <div className="text-[#71717a] text-xs">{(bet.stakeFrac * 100).toFixed(2)}%</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6 auto-rows-fr">
                  {topProps.map((prop: PropEdge, idx: number) => (
                    <PropCard
                      key={`${prop.player_id}-${prop.prop_type}-${idx}`}
                      rank={idx + 1}
                      playerName={prop.player_name}
                      team={prop.team}
                      opponent={prop.opponent}
                      propType={prop.prop_type}
                      line={prop.line}
                      overOdds={prop.over_odds}
                      underOdds={prop.under_odds}
                      projectedValue={prop.projected_value}
                      hitRateSeason={prop.hit_rate_season}
                      hitRateLast10={prop.hit_rate_last10}
                      hitRateLast5={prop.hit_rate_last5}
                      modelProbOver={prop.model_prob_over}
                      marketProbOver={prop.market_prob_over}
                      edgePct={prop.edge_pct}
                      evOver={prop.ev_over}
                      evUnder={prop.ev_under}
                      decimalOver={prop.decimal_over}
                      decimalUnder={prop.decimal_under}
                      stakeFracOver={prop.stake_frac_over}
                      stakeFracUnder={prop.stake_frac_under}
                      stakeDollarsOver={prop.stake_dollars_over}
                      stakeDollarsUnder={prop.stake_dollars_under}
                      recommendedSide={prop.recommended_side}
                      confidence={prop.confidence}
                      sampleSize={prop.sample_size}
                      vsOpponentAvg={prop.vs_opponent_avg}
                      trend={prop.trend}
                      book={prop.book}
                    />
                  ))}
                </div>
              </>
            )}
          </>
        )}

        {view === 'cash' && (
          <div className="mt-12 border-t border-[#2a2a35] pt-12">
            <h2 className="text-2xl font-bold text-[#f0f0f5] mb-6 text-center">Cash & Parlays</h2>

            {/* CASH Section - Top 5 Best Bets */}
            {cashAllocation.length > 0 && (
              <div className="mb-8 bg-gradient-to-br from-green-900/30 to-emerald-900/20 border-2 border-green-500/50 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">💰</span>
                    <div>
                      <h2 className="text-xl font-bold text-green-400">CASH</h2>
                      <p className="text-xs text-green-400/70">Top 5 Bets - Optimized for Max Profit</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-green-400 font-mono">${totalCashAmount.toFixed(2)}</div>
                    <div className="text-xs text-green-400/70">Total to bet tonight</div>
                  </div>
                </div>

                <div className="space-y-3">
                  {cashAllocation.map((bet, idx) => (
                    <div
                      key={`${bet.id}-${idx}`}
                      className="bg-[#0a0a0f]/60 rounded-xl p-4 flex items-center justify-between border border-green-500/20"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 font-bold">
                          {idx + 1}
                        </div>
                        <div>
                          <div className="text-[#f0f0f5] font-semibold">{bet.label}</div>
                          <div className="flex items-center gap-2 text-xs">
                            <span className={`font-semibold ${bet.type === 'game' ? 'text-blue-400' : 'text-orange-400'}`}>
                              {bet.type === 'game' ? 'GAME' : 'PROP'}
                            </span>
                            <span className="text-[#71717a]">•</span>
                            <span className="text-green-400 font-medium">{bet.pick}</span>
                            <span className="text-[#71717a]">•</span>
                            <span className="text-[#71717a]">{bet.odds > 0 ? `+${bet.odds}` : bet.odds}</span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-bold text-green-400 font-mono">${bet.allocatedAmount.toFixed(2)}</div>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-[#71717a]">{bet.allocatedPct.toFixed(1)}%</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            bet.confidence === 'high' ? 'bg-green-500/20 text-green-400' :
                            bet.confidence === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-gray-500/20 text-gray-400'
                          }`}>
                            {bet.confidence?.toUpperCase()}
                          </span>
                          <span className="text-green-400/70">+{(bet.ev * 100).toFixed(0)}% EV</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 pt-4 border-t border-green-500/20 flex justify-between items-center text-sm">
                  <div className="text-green-400/70">
                    Expected return: <span className="text-green-400 font-mono font-semibold">
                      +${cashAllocation.reduce((sum, b) => sum + (b.allocatedAmount * b.ev), 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="text-green-400/70">
                    Avg edge: <span className="text-green-400 font-mono font-semibold">
                      {(cashAllocation.reduce((sum, b) => sum + b.edge, 0) / cashAllocation.length).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* PARLAY Section */}
            {parlayEligible.length >= 2 && (
              <div className="grid grid-cols-1 gap-6">
                <div className="bg-gradient-to-br from-cyan-900/30 to-teal-900/20 border-2 border-cyan-500/50 rounded-2xl p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-2xl">🔒</span>
                    <div>
                      <h2 className="text-lg font-bold text-cyan-400">PARLAY</h2>
                      <p className="text-xs text-cyan-400/70">Best Odds to Actually Hit</p>
                    </div>
                  </div>

                  <div className="space-y-2 mb-4">
                    {bestOddsLegs.map((leg, idx) => (
                      <div key={`safe-leg-${idx}`} className="bg-[#0a0a0f]/60 rounded-lg p-3 border border-cyan-500/20">
                        <div className="flex justify-between items-center">
                          <div>
                            <span className={`text-xs font-semibold ${leg.type === 'game' ? 'text-blue-400' : 'text-orange-400'}`}>
                              {leg.type === 'game' ? 'GAME' : 'PROP'}
                            </span>
                            <div className="text-[#f0f0f5] font-medium text-sm">{leg.label}</div>
                            <div className="text-cyan-400 text-xs">{leg.pick}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-[#f0f0f5] font-mono">{leg.odds > 0 ? `+${leg.odds}` : leg.odds}</div>
                            <div className="text-cyan-400/70 text-xs">
                              {(((1 + leg.ev) / toDecimal(leg.odds)) * 100).toFixed(0)}% prob
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="bg-[#0a0a0f]/80 rounded-xl p-4 border border-cyan-500/30">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="text-xs text-cyan-400/70 uppercase">Parlay Odds</div>
                        <div className="text-2xl font-bold text-cyan-400 font-mono">
                          {bestOddsParlay.americanOdds > 0 ? `+${bestOddsParlay.americanOdds}` : bestOddsParlay.americanOdds}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-cyan-400/70 uppercase">Win Prob</div>
                        <div className="text-lg font-bold text-[#f0f0f5] font-mono">{(bestOddsParlay.winProb * 100).toFixed(1)}%</div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-cyan-400/70 uppercase">Parlay EV</div>
                        <div className={`text-lg font-bold font-mono ${bestOddsParlay.ev > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {bestOddsParlay.ev > 0 ? '+' : ''}{(bestOddsParlay.ev * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Legend */}
        {(view === 'games' || view === 'props') && (
          <div className="mt-12 p-6 bg-[#12121a] border border-[#2a2a35] rounded-xl">
            <h3 className="text-sm font-semibold text-[#f0f0f5] mb-4">
              {view === 'games' ? 'Game Lines Guide' : 'Player Props Guide'}
            </h3>
            {view === 'games' ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span className="text-[#f0f0f5] font-medium">Edge Detected</span>
                  </div>
                  <p className="text-[#71717a]">
                    Model finds value vs market odds. Green glow = recommended bet.
                  </p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span className="text-[#f0f0f5] font-medium">Out</span>
                    <div className="w-3 h-3 rounded-full bg-yellow-500 ml-2" />
                    <span className="text-[#f0f0f5] font-medium">Day-to-Day</span>
                  </div>
                  <p className="text-[#71717a]">
                    Injury status indicators. Impact factored into Elo adjustment.
                  </p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-green-400 font-mono font-bold">+18.9%</span>
                    <span className="text-[#f0f0f5] font-medium">Edge %</span>
                  </div>
                  <p className="text-[#71717a]">
                    Model probability minus market implied probability.
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-green-400 font-semibold">OVER</span>
                    <span className="text-red-400 font-semibold">UNDER</span>
                  </div>
                  <p className="text-[#71717a]">
                    Recommended side based on model projection vs line.
                  </p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[#f0f0f5] font-medium">Hit Rate</span>
                  </div>
                  <p className="text-[#71717a]">
                    % of games player has gone over the line. Season, L10, L5.
                  </p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-green-400">↑</span>
                    <span className="text-[#71717a]">→</span>
                    <span className="text-red-400">↓</span>
                    <span className="text-[#f0f0f5] font-medium">Trend</span>
                  </div>
                  <p className="text-[#71717a]">
                    Recent performance trend based on last 3-6 games.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#2a2a35] mt-12">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <p className="text-center text-[#71717a] text-sm">
            Sports Edge | Game Lines + Player Props Analysis | Not financial advice
          </p>
        </div>
      </footer>
    </div>
  );
}
