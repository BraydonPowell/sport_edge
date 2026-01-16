'use client';

export default function Header() {
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <header className="neon-header sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#402fb5] via-[#6ad7ff] to-[#cf30aa] flex items-center justify-center shadow-[0_0_20px_rgba(207,48,170,0.4)]">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#f2f2f7]">Sports Edge</h1>
            </div>
          </div>

          {/* Date */}
          <div className="text-right">
            <div className="text-sm neon-muted">Today</div>
            <div className="text-[#f2f2f7] font-medium">{today}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
