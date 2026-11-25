export function Logo({ className = "size-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="#6E58A8" />
      <path d="M8 22V10.5l8 6.5 8-6.5V22" fill="none" stroke="#EAE2F8" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="24.5" cy="8" r="2.2" fill="#A8C9B0" />
    </svg>
  );
}
