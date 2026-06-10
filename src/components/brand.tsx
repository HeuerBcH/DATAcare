interface LogoProps {
  size?: number;
  className?: string;
}

/** Marca do DATAcare: um traçado de ECG dentro de um quadrado arredondado. */
export function Logo({ size = 36, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <rect width="40" height="40" rx="11" fill="#0f766e" />
      <path
        d="M6 21.5h5.2l2.6-7.5 4.2 15 3-10.5 2.1 3.5H34"
        stroke="#a8edd2"
        strokeWidth="2.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="33.5" cy="22" r="2" fill="#6fdcb7" />
    </svg>
  );
}

export function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`font-display text-xl font-600 tracking-tight text-ink ${className}`}>
      DATA<span className="text-brand-700">care</span>
    </span>
  );
}
