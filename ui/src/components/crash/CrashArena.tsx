import { useMemo, useState } from 'react';

import { getTonConnectConfig } from '../../api-client/wallet';
import { BalanceActions } from './BalanceActions';
import { BettingPanel } from './BettingPanel';
import { CrashGraph } from './CrashGraph';
import { LivePlayers } from './LivePlayers';
import { MultiplierDisplay } from './MultiplierDisplay';
import { RewardOverlay } from './RewardOverlay';
import { RoundHistory } from './RoundHistory';

export function CrashArena() {
  const [tonBalance] = useState('0.00');
  const [starsBalance] = useState('0');

  const botUsername = useMemo(() => import.meta.env.VITE_BOT_USERNAME ?? '', []);

  const handleAddTon = async () => {
    try {
      const config = await getTonConnectConfig();
      const encodedManifest = encodeURIComponent(config.manifest_url);
      window.open(`https://app.tonkeeper.com/ton-connect?manifestUrl=${encodedManifest}`, '_blank');
    } catch (error) {
      window.alert(`TON connect init failed: ${(error as Error).message}`);
    }
  };

  const handleAddStars = async () => {
    try {
      if (botUsername) {
        window.open(`https://t.me/${botUsername}?start=addstars_1`, '_blank');
      } else {
        window.alert('Bot username is not configured. Set VITE_BOT_USERNAME.');
      }
    } catch (error) {
      window.alert(`Stars invoice creation failed: ${(error as Error).message}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 p-3 text-white">
      <BalanceActions
        tonBalance={tonBalance}
        starsBalance={starsBalance}
        onAddTon={handleAddTon}
        onAddStars={handleAddStars}
      />
      <RoundHistory />
      <div className="space-y-4 rounded-3xl border border-slate-700/50 bg-slate-900/60 p-4 backdrop-blur-xl">
        <MultiplierDisplay value="1.00x" state="waiting" />
        <CrashGraph />
      </div>
      <LivePlayers />
      <BettingPanel />
      <RewardOverlay />
    </div>
  );
}
