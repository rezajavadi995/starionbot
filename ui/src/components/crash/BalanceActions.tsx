export function BalanceActions({
  tonBalance = '0.00',
  starsBalance = '0',
  onAddTon,
  onAddStars,
}: {
  tonBalance?: string;
  starsBalance?: string;
  onAddTon?: () => void;
  onAddStars?: () => void;
}) {
  return (
    <div className="mb-3 flex items-center justify-end gap-2">
      <button
        type="button"
        onClick={onAddStars}
        className="flex items-center gap-2 rounded-xl border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/20"
      >
        <span className="text-base">⭐</span>
        <span>{starsBalance}</span>
        <span className="rounded-lg bg-amber-400/20 px-2 py-0.5">+ Stars</span>
      </button>

      <button
        type="button"
        onClick={onAddTon}
        className="flex items-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/20"
      >
        <span className="text-base">💎</span>
        <span>{tonBalance} TON</span>
        <span className="rounded-lg bg-cyan-400/20 px-2 py-0.5">+ TON</span>
      </button>
    </div>
  );
}
