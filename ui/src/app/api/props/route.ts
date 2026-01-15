import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const league = searchParams.get('league') || 'NBA';
  if (league !== 'NBA') {
    return NextResponse.json([]);
  }
  try {
    const projectRoot = '/Users/braydonpowell/Sports_edge';

    const bankroll = searchParams.get('bankroll') || '';
    const leagueEnv = `PROPS_LEAGUE=${league} `;
    const bankrollEnv = bankroll ? `BANKROLL=${bankroll} ` : '';
    const { stdout, stderr } = await execAsync(
      `source ${projectRoot}/venv/bin/activate && cd ${projectRoot} && ${leagueEnv}${bankrollEnv}python3 ${projectRoot}/scripts/live_props.py`,
      { shell: '/bin/bash', timeout: 60000 }  // 60 second timeout for API calls
    );

    if (stderr) {
      console.log('Python stderr:', stderr);
    }

    const props = JSON.parse(stdout.trim());
    return NextResponse.json(props);
  } catch (error) {
    console.error('Props API error:', error);

    return NextResponse.json({ props: [], error: String(error) });
  }
}
