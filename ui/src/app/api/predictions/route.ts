import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

export async function GET(request: Request) {
  try {
    const projectRoot = path.resolve(process.cwd(), '..');
    const { searchParams } = new URL(request.url);
    const bankroll = searchParams.get('bankroll') || '';
    const bankrollEnv = bankroll ? `BANKROLL=${bankroll} ` : '';
    const { stdout } = await execAsync(
      `source ${projectRoot}/venv/bin/activate && ${bankrollEnv}python3 ${projectRoot}/scripts/live_games.py`,
      { shell: '/bin/bash', timeout: 60000 }
    );

    const payload = JSON.parse(stdout.trim());
    return NextResponse.json(payload);
  } catch (error) {
    console.error('Prediction error:', error);
    return NextResponse.json({ games: [], error: 'Failed to load live games.' });
  }
}
