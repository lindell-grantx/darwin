interface Props {
  size?: 'sm' | 'md';
  label?: string;
  className?: string;
}

export function Spinner({ size = 'md', label, className = '' }: Props) {
  const dim = size === 'sm' ? 'h-3 w-3' : 'h-5 w-5';
  const border = size === 'sm' ? 'border-[1.5px]' : 'border-2';
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div className="relative">
        <div
          role="status"
          aria-label={label ?? 'Loading'}
          className={`${dim} ${border} animate-spin rounded-full border-rule border-t-brass-bright`}
        />
      </div>
      {label && (
        <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-bone-fade">
          {label}
        </span>
      )}
    </div>
  );
}
