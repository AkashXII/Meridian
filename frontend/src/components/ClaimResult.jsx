import React from 'react';
import Header from './Header.jsx';
import { badgeFor, badgeStyle, formatAmount } from './ui.js';

export default function ClaimResult({
  setAuthToken,
  currentScreen,
  setCurrentScreen,
  claimResult,
  userRole,
}) {
  if (!claimResult) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-on-surface-variant">No claim selected. Go back and submit or select one.</p>
      </div>
    );
  }

  const missingFields = claimResult.missing_fields ?? [];
  const needsClarification = missingFields.length > 0;

  const policyNumber = claimResult.extracted?.policy_number ?? claimResult.policy_number;
  const claimType = claimResult.extracted?.claim_type ?? claimResult.claim_type;
  const incidentDate = claimResult.extracted?.incident_date ?? claimResult.incident_date;
  const amountRequested = claimResult.extracted?.amount_requested ?? claimResult.amount_requested;
  const decision = claimResult.decision ?? claimResult.final_decision;
  const reasoning = claimResult.reasoning ?? claimResult.coverage_reasoning;
  const fraudFlagged = claimResult.fraud_flagged;
  const fraudReason = claimResult.fraud_reason;

  // The AI's own assessment is stored separately from the final decision.
  // Show it when they differ (e.g. AI approved, fraud rule escalated to review).
  const aiDecision = claimResult.coverage_decision;
  const showAiDecision = !needsClarification && aiDecision && aiDecision !== decision;

  const badge = needsClarification ? badgeFor('info') : badgeFor(decision);

  const fields = [
    { label: 'Policy number', value: policyNumber || '—', mono: true },
    { label: 'Claim type', value: claimType || '—', capitalize: true },
    { label: 'Incident date', value: incidentDate || '—', mono: true },
    { label: 'Amount claimed', value: formatAmount(amountRequested), mono: true },
  ];

  return (
    <div className="bg-background text-on-surface font-body-md min-h-screen flex flex-col">
      <Header
        currentScreen={currentScreen}
        setCurrentScreen={setCurrentScreen}
        setAuthToken={setAuthToken}
        userRole={userRole}
      />

      <main className="flex-grow w-full max-w-[1200px] mx-auto px-margin-mobile md:px-margin-desktop py-10">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between gap-4 mb-6">
            <h1 className="font-display-lg text-display-lg text-primary">Claim decision</h1>
            <span className="status" style={badgeStyle(badge)}>{badge.label}</span>
          </div>

          {needsClarification ? (
            <div className="bg-white border border-outline-variant rounded-DEFAULT p-6">
              <h2 className="font-headline-sm text-headline-sm text-primary mb-2">More information needed</h2>
              <p className="font-body-md text-body-md text-on-surface-variant mb-3">
                We couldn't process this claim because some details were missing:
              </p>
              <ul className="list-disc pl-5 font-body-md text-body-md text-on-surface space-y-1">
                {missingFields.map((field) => (
                  <li key={field}>{field.replace(/_/g, ' ')}</li>
                ))}
              </ul>
              <p className="font-body-md text-body-md text-on-surface-variant mt-4">
                Please submit the claim again with these details included.
              </p>
            </div>
          ) : (
            <div className="bg-white border border-outline-variant rounded-DEFAULT">
              <dl className="grid grid-cols-2 md:grid-cols-4 border-b border-outline-variant">
                {fields.map((f, i) => (
                  <div
                    key={f.label}
                    className={`p-5 ${i > 0 ? 'md:border-l border-outline-variant' : ''} ${
                      i % 2 === 1 ? 'border-l md:border-l' : ''
                    } ${i > 1 ? 'border-t md:border-t-0' : ''}`}
                  >
                    <dt className="text-[12.5px] text-on-surface-variant mb-1">{f.label}</dt>
                    <dd
                      className={`${f.mono ? 'font-data-tabular text-data-tabular' : 'text-[14px]'} text-on-surface ${
                        f.capitalize ? 'capitalize' : ''
                      }`}
                    >
                      {f.value}
                    </dd>
                  </div>
                ))}
              </dl>

              <div className="p-6 border-b border-outline-variant">
                <h2 className="font-headline-sm text-headline-sm text-primary mb-2">Reasoning</h2>
                <p className="font-body-md text-body-md text-on-surface leading-relaxed">
                  {reasoning || 'No reasoning available.'}
                </p>
                {showAiDecision && (
                  <p className="text-[13px] text-on-surface-variant mt-3">
                    Automated coverage assessment:{' '}
                    <span className="font-medium text-on-surface">{badgeFor(aiDecision).label.toLowerCase()}</span>
                  </p>
                )}
              </div>

              <div className="p-6 flex items-start gap-3">
                <span className="text-[13px] text-on-surface-variant w-28 shrink-0 pt-0.5">Fraud check</span>
                {fraudFlagged ? (
                  <div>
                    <span className="status" style={badgeStyle(badgeFor('needs_review'))}>Flagged</span>
                    <p className="font-body-md text-body-md text-on-surface mt-2">{fraudReason}</p>
                  </div>
                ) : (
                  <span className="status" style={badgeStyle(badgeFor('approved'))}>Passed</span>
                )}
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setCurrentScreen('submit')}
              className="px-4 py-2 border border-outline-variant bg-white text-primary text-[14px] rounded-DEFAULT hover:bg-surface transition-colors cursor-pointer"
            >
              Submit another claim
            </button>
            <button
              type="button"
              onClick={() => setCurrentScreen('history')}
              className="px-4 py-2 bg-primary-container text-on-primary text-[14px] font-medium rounded-DEFAULT hover:bg-on-primary-fixed-variant transition-colors cursor-pointer"
            >
              Back to history
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
