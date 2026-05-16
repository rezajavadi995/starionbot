import { useState } from 'react';

type BetAsset = 'stars' | 'ton';

export function BettingPanel() {
  const [asset, setAsset] = useState<BetAsset>('stars');

  return (
    <div className="mt-3 rounded-2xl border border-slate-700/60 bg-slate-800/50 p-3 shadow-2xl shadow-cyan-950/30">
      <div className="mb-3 grid grid-cols-2 gap-2 rounded-2xl bg-slate-950/60 p-1">
        <button
          type="button"
          onClick={() => setAsset('stars')}
          className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
            asset === 'stars'
              ? 'bg-amber-400/20 text-amber-200 shadow-lg shadow-amber-500/10'
              : 'text-slate-400'
          }`}
        >
          Play with Stars
        </button>
        <button
          type="button"
          onClick={() => setAsset('ton')}
          className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
            asset === 'ton'
              ? 'bg-cyan-400/20 text-cyan-200 shadow-lg shadow-cyan-500/10'
              : 'text-slate-400'
          }`}
        >
          Play with TON
        </button>
      </div>
      <div className="text-xs text-slate-400">
        Selected balance: <span className="font-semibold uppercase text-white">{asset}</span>
      </div>
    </div>
  );
}
