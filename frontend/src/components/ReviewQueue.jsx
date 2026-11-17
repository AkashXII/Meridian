import React, { useEffect, useState } from 'react';
import Header from './Header.jsx';
import { badgeFor, badgeStyle, formatAmount } from './ui.js';

// Rows written before confidence_schema.sql have no escalation_reason;
// fall back to the fraud reason, which was the only escalation path then.
// A clean fraud check's reason ("No deterministic rule violations...") is
// not an escalation reason, so it is only shown when the claim was flagged.
const escalationText = (c) =>
  c.escalation_reason ||
  (c.fraud_flagged ? c.fraud_reason : null) ||
  (c.coverage_decision === 'needs_review' ? 'The automated assessment itself asked for review.' : null);

export default function ReviewQueue({ authToken, setAuthToken, userRole, currentScreen, setCurrentScreen }) {
  const [queue, setQueue] = useState([]);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const loadQueue = () => {
    setLoading(true);
    fetch('http://localhost:8000/review/queue', {
      headers: { Authorization: `Bearer ${authToken}` },
    })
      .then((res) =>
        res.json().then((data) => {
          if (!res.ok) throw new Error(data.detail || 'Could not load queue');
          return data;
        })
      )
      .then((data) => setQueue(data.queue || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadQueue, [authToken]);

  const resolve = async (decision) => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/review/${selected.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ decision, notes }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not resolve claim');
      setSelected(null);
      setNotes('');
      loadQueue();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const th = 'py-2.5 px-4 text-[12.5px] font-medium text-on-surface-variant';

  return (
    <div className="text-on-surface font-body-md min-h-screen flex flex-col bg-background">
      <Header
        currentScreen={currentScreen}
        setCurrentScreen={setCurrentScreen}
        setAuthToken={setAuthToken}
        userRole={userRole}
      />

      <main className="flex-grow w-full max-w-[1200px] mx-auto px-margin-mobile md:px-margin-desktop py-10">
        <div className="mb-6">
          <h1 className="font-headline-md text-headline-md text-on-surface">Review queue</h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Claims the automated pipeline escalated for a human decision.
          </p>
        </div>

        {error && (
          <p className="mb-4" style={{ color: '#b91c1c' }}>
            {error}
          </p>
        )}
        {loading && <p className="text-on-surface-variant">Loading queue…</p>}

        {!loading && queue.length === 0 && (
          <div className="bg-white border border-outline-variant rounded-DEFAULT p-8 text-center">
            <p className="text-on-surface-variant">Nothing is waiting for review.</p>
          </div>
        )}

        {!loading && queue.length > 0 && (
          <div className="w-full overflow-x-auto bg-white border border-outline-variant rounded-DEFAULT">
            <table className="w-full text-left border-collapse min-w-[760px]">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-low">
                  <th className={th}>Date</th>
                  <th className={th}>Policy</th>
                  <th className={th}>Type</th>
                  <th className={th}>Flagged for</th>
                  <th className={`${th} text-right`}>Amount</th>
                </tr>
              </thead>
              <tbody className="text-on-surface">
                {queue.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => {
                      setSelected(c);
                      setNotes('');
                    }}
                    className={`border-b border-outline-variant last:border-b-0 hover:bg-surface transition-colors cursor-pointer ${
                      selected?.id === c.id ? 'bg-accent-soft' : ''
                    }`}
                  >
                    <td className="py-3 px-4 font-data-tabular text-data-tabular">{c.created_at?.slice(0, 10)}</td>
                    <td className="py-3 px-4 font-data-tabular text-data-tabular">{c.policy_number || '—'}</td>
                    <td className="py-3 px-4 text-[14px] capitalize">{c.claim_type || '—'}</td>
                    <td className="py-3 px-4 text-[13px] text-on-surface-variant max-w-[420px]">{escalationText(c) || '—'}</td>
                    <td className="py-3 px-4 text-right font-data-tabular text-data-tabular">
                      {formatAmount(c.amount_requested)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selected && (
          <div className="mt-6 bg-white border border-outline-variant rounded-DEFAULT">
            <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between">
              <h2 className="font-headline-sm text-headline-sm text-primary">Reviewing claim #{selected.id}</h2>
              <span className="font-data-tabular text-data-tabular text-on-surface-variant">
                {selected.policy_number} · {formatAmount(selected.amount_requested)}
              </span>
            </div>

            <div className="p-6 space-y-5">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[13px] text-on-surface-variant">Automated assessment</span>
                  {selected.coverage_decision && (
                    <span className="status" style={badgeStyle(badgeFor(selected.coverage_decision))}>
                      {badgeFor(selected.coverage_decision).label}
                    </span>
                  )}
                </div>
                <p className="font-body-md text-body-md text-on-surface leading-relaxed">
                  {selected.coverage_reasoning}
                </p>
              </div>

              <div>
                <span className="block text-[13px] text-on-surface-variant mb-1.5">Why it was escalated</span>
                <p className="font-body-md text-body-md text-on-surface">{escalationText(selected) || 'None'}</p>
              </div>

              <div>
                <label className="block text-[13px] text-on-surface-variant mb-1.5" htmlFor="notes">
                  Reviewer notes
                </label>
                <textarea
                  id="notes"
                  rows="3"
                  className="w-full border border-outline-variant px-3 py-2 font-body-md text-body-md bg-white text-on-surface"
                  placeholder="Why are you approving or denying this claim?"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => resolve('approved')}
                  className="px-5 py-2 text-[14px] font-medium rounded-DEFAULT cursor-pointer disabled:opacity-50"
                  style={{ background: '#1c1917', color: '#ffffff' }}
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => resolve('denied')}
                  className="px-5 py-2 text-[14px] font-medium rounded-DEFAULT cursor-pointer disabled:opacity-50"
                  style={{ background: '#ffffff', color: '#1c1917', border: '1px solid #d6d3d1' }}
                >
                  Deny
                </button>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="px-4 py-2 text-[14px] text-on-surface-variant hover:text-primary cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
