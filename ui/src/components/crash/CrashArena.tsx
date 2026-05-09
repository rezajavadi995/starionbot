import { BettingPanel } from './BettingPanel';
import { CrashGraph } from './CrashGraph';
import { LivePlayers } from './LivePlayers';
import { MultiplierDisplay } from './MultiplierDisplay';
import { RewardOverlay } from './RewardOverlay';
import { RoundHistory } from './RoundHistory';

export function CrashArena() {
  return (
    <div className="min-h-screen bg-slate-950 text-white p-3">
      <RoundHistory />
      <div className="rounded-3xl border border-slate-700/50 bg-slate-900/60 backdrop-blur-xl p-4 space-y-4">
        <MultiplierDisplay value="1.00x" state="waiting" />
        <CrashGraph />
      </div>
      <LivePlayers />
      <BettingPanel />
      <RewardOverlay />
    </div>
  );
}
