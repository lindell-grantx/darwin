interface Props {
  size?: 'sm' | 'md';
  label?: string;
  className?: string;
}

export function Spinner({ size = 'md', label, className = '' }: Props) {
  const dim = size === 'sm' ? 'h-3 w-3 border-2' : 'h-5 w-5 border-2';
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        role="status"
        aria-label={label ?? 'Loading'}
        className={`${dim} animate-spin rounded-full border-zinc-700 border-t-emerald-400`}
      />
      {label && <span className="text-xs text-zinc-500">{label}</span>}
    </div>
  );
}
