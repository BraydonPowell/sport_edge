'use client';

export default function Header() {
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <header className="border-b border-[#2a2a35] bg-[#0a0a0f]/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-black"
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
              <h1 className="text-xl font-bold text-[#f0f0f5]">Sports Edge</h1>
              <p className="text-xs text-[#71717a]">AI-Powered Betting Intelligence</p>
            </div>
          </div>

          {/* Date */}
          <div className="text-right">
            <div className="text-sm text-[#71717a]">Today</div>
            <div className="text-[#f0f0f5] font-medium">{today}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
