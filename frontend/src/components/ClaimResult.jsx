import React from 'react';

export default function ClaimResult({ setAuthToken, currentScreen, setCurrentScreen, claimResult }) {
  const handlePrint = () => {
    window.print();
  };

  if (!claimResult) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest">
        <p className="text-on-surface-variant">No claim selected. Go back and submit or select one.</p>
      </div>
    );
  }


  const policyNumber = claimResult.extracted?.policy_number ?? claimResult.policy_number;
  const claimType = claimResult.extracted?.claim_type ?? claimResult.claim_type;
  const incidentDate = claimResult.extracted?.incident_date ?? claimResult.incident_date;
  const amountRequested = claimResult.extracted?.amount_requested ?? claimResult.amount_requested;
  const decision = claimResult.decision ?? claimResult.final_decision;
  const reasoning = claimResult.reasoning ?? claimResult.coverage_reasoning;
  const fraudFlagged = claimResult.fraud_flagged;
  const fraudReason = claimResult.fraud_reason;

  const badge = {
    approved: { bg: '#DEF7EC', text: '#03543F', label: 'APPROVED' },
    denied: { bg: '#FDE8E8', text: '#9B1C1C', label: 'DENIED' },
    needs_review: { bg: '#FDF6B2', text: '#723B13', label: 'NEEDS REVIEW' },
  }[decision] || { bg: '#E5E7EB', text: '#374151', label: 'UNKNOWN' };

  return (
    <div className="bg-background text-on-surface font-body-md min-h-screen flex flex-col">
<header className="bg-surface-container-lowest border-b border-outline-variant w-full">
  <div className="relative flex items-center w-full px-margin-desktop py-4">
    <div
      className="font-headline-sm text-headline-sm font-bold text-primary cursor-pointer"
      onClick={() => setCurrentScreen('submit')}
    >
      ClaimsPortal
    </div>
    <nav className="hidden md:flex gap-6 items-center absolute left-1/2 -translate-x-1/2">
      <button
        type="button"
        onClick={() => setCurrentScreen('submit')}
        className={`font-body-md text-body-md pb-1 cursor-pointer transition-colors duration-150 ${
          currentScreen === 'submit'
            ? 'text-primary border-b-2 border-primary font-bold'
            : 'text-on-surface-variant hover:text-primary'
        }`}
      >
        Submit a Claim
      </button>
      <button
        type="button"
        onClick={() => setCurrentScreen('history')}
        className={`font-body-md text-body-md pb-1 cursor-pointer transition-colors duration-150 ${
          currentScreen === 'history' || currentScreen === 'result'
            ? 'text-primary border-b-2 border-primary font-bold'
            : 'text-on-surface-variant hover:text-primary'
        }`}
      >
        Claim History
      </button>
    </nav>
    <button
      type="button"
      onClick={() => setAuthToken(null)}
      className="ml-auto font-body-md text-body-md text-on-surface-variant cursor-pointer hover:text-primary transition-colors"
    >
      Log Out
    </button>
  </div>
</header>

      <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-margin-desktop">
        <div className="max-w-3xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-outline-variant pb-stack-md mb-stack-lg gap-stack-sm">
            <h1 className="font-display-lg text-display-lg text-primary">Claim Decision</h1>
            <div
              className="inline-flex items-center justify-center px-3 py-1 rounded font-label-md text-label-md tracking-wider"
              style={{ background: badge.bg, color: badge.text }}
            >
              {badge.label}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-y-stack-md gap-x-gutter mb-stack-lg border border-outline-variant rounded-lg p-stack-lg bg-surface-container-lowest">
            <div className="flex flex-col gap-unit">
              <span className="font-label-md text-label-md text-on-surface-variant">Policy Number</span>
              <span className="font-data-tabular text-data-tabular text-on-surface">{policyNumber || '—'}</span>
            </div>
            <div className="flex flex-col gap-unit">
              <span className="font-label-md text-label-md text-on-surface-variant">Claim Type</span>
              <span className="font-data-tabular text-data-tabular text-on-surface capitalize">{claimType || '—'}</span>
            </div>
            <div className="flex flex-col gap-unit">
              <span className="font-label-md text-label-md text-on-surface-variant">Incident Date</span>
              <span className="font-data-tabular text-data-tabular text-on-surface">{incidentDate || '—'}</span>
            </div>
            <div className="flex flex-col gap-unit">
              <span className="font-label-md text-label-md text-on-surface-variant">Amount</span>
              <span className="font-data-tabular text-data-tabular text-on-surface">
                {amountRequested != null ? `$${Number(amountRequested).toFixed(2)}` : '—'}
              </span>
            </div>
          </div>

          <div className="mb-stack-lg">
            <h2 className="font-headline-sm text-headline-sm text-primary mb-stack-sm">Reasoning</h2>
            <div className="p-stack-md bg-surface border border-outline-variant rounded-DEFAULT">
              <p className="font-body-md text-body-md text-on-surface">
                {reasoning || 'No reasoning available.'}
              </p>
            </div>
          </div>

          <div className="pt-stack-md border-t border-outline-variant">
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Fraud Check: </span>
            <span className="font-body-md text-body-md text-on-surface">
              {fraudFlagged ? `Flagged — ${fraudReason}` : 'Passed'}
            </span>
          </div>

          <div className="mt-margin-desktop flex justify-end gap-stack-md">
 
            <button
              type="button"
              onClick={() => setCurrentScreen('history')}
              className="px-6 py-2 bg-primary-container text-on-primary border border-transparent rounded-DEFAULT hover:bg-on-primary-fixed-variant transition-colors font-label-md text-label-md cursor-pointer"
            >
              Return to History
            </button>
          </div>
        </div>
      </main>

      <footer className="bg-surface-container border-t border-outline-variant mt-auto">

      </footer>
    </div>
  );
}