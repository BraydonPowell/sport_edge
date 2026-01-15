export interface Prediction {
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
}

export interface Injury {
  player: string;
  team: string;
  status: 'Out' | 'Day-To-Day' | 'Questionable';
  impact: number;
  description: string;
}

export interface TeamInjuries {
  team: string;
  injuries: Injury[];
  totalImpact: number;
}
