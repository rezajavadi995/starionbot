type RoundState = 'waiting' | 'active' | 'crashed';

type MultiplierDisplayProps = {
  value: string;
  state: RoundState;
};

const stateClassMap: Record<RoundState, string> = {
  waiting: 'text-slate-300',
  active: 'text-emerald-400',
  crashed: 'text-rose-500',
};

export function MultiplierDisplay({ value, state }: MultiplierDisplayProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`text-5xl font-black tracking-tight ${stateClassMap[state]}`}>{value}</div>
      <div className="text-xs uppercase text-slate-400">{state}</div>
    </div>
  );
}
