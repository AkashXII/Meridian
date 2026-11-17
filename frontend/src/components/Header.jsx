import React from 'react';

// One header for every signed-in screen (previously copied into each file).
export default function Header({ currentScreen, setCurrentScreen, setAuthToken, userRole }) {
  const tabs = [
    { id: 'submit', label: 'Submit claim' },
    { id: 'history', label: 'Claim history' },
  ];
  if (userRole === 'reviewer') tabs.push({ id: 'review', label: 'Review queue' });

  // A claim's result page belongs under "Claim history".
  const active = currentScreen === 'result' ? 'history' : currentScreen;

  return (
    <header className="bg-white border-b border-outline-variant">
      <div className="max-w-[1200px] mx-auto px-margin-mobile md:px-margin-desktop h-14 flex items-center gap-8">
        <button
          type="button"
          onClick={() => setCurrentScreen('submit')}
          className="flex items-baseline gap-2 cursor-pointer"
        >
          <span className="text-[17px] font-semibold tracking-tight text-primary">Meridian</span>
          <span className="text-[12px] text-on-surface-variant">Claims</span>
        </button>

        <nav className="hidden md:flex items-stretch gap-1 h-full">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setCurrentScreen(t.id)}
              className={`px-3 text-[14px] border-b-2 transition-colors cursor-pointer ${
                active === t.id
                  ? 'border-accent text-primary font-medium'
                  : 'border-transparent text-on-surface-variant hover:text-primary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-4">
          {userRole === 'reviewer' && (
            <span className="text-[12px] px-2 py-0.5 rounded-full border border-outline-variant text-on-surface-variant">
              Reviewer
            </span>
          )}
          <button
            type="button"
            onClick={() => setAuthToken(null)}
            className="text-[14px] text-on-surface-variant hover:text-primary cursor-pointer"
          >
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
