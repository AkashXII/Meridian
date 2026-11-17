import React, { useState } from 'react';
import Header from './Header.jsx';

export default function SubmitClaim({
  authToken,
  setAuthToken,
  currentScreen,
  setCurrentScreen,
  setClaimResult,
  userRole,
}) {
  const [claimDescription, setClaimDescription] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/claims', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ claim_text: claimDescription }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Claim submission failed');

      setClaimResult(data);
      setCurrentScreen('result');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-background text-on-background min-h-screen flex flex-col">
      <Header
        currentScreen={currentScreen}
        setCurrentScreen={setCurrentScreen}
        setAuthToken={setAuthToken}
        userRole={userRole}
      />

      <main className="flex-grow w-full max-w-[1200px] mx-auto px-margin-mobile md:px-margin-desktop py-12">
        <div className="max-w-2xl mx-auto">
          <div className="mb-6">
            <h1 className="font-display-lg text-display-lg text-on-surface">Submit a claim</h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant mt-1">
              Describe what happened in your own words. The claim is checked against your policy and you get a
              decision with the reasoning behind it.
            </p>
          </div>

          <form
            className="bg-white border border-outline-variant rounded-DEFAULT p-6 space-y-5"
            onSubmit={handleSubmit}
          >
            <div>
              <label className="block font-label-md text-label-md text-on-surface mb-1.5" htmlFor="claim-description">
                What happened?
              </label>

              <textarea
                className="w-full bg-white border border-outline-variant px-3 py-2.5 font-body-md text-body-md text-on-surface resize-y"
                id="claim-description"
                placeholder="e.g. A tree branch fell on my car on 2026-11-08. Policy A-77821. The repair estimate is $650."
                rows="7"
                value={claimDescription}
                onChange={(e) => setClaimDescription(e.target.value)}
              ></textarea>

              <p className="text-[13px] text-on-surface-variant mt-2">
                Include your policy number, the date of the incident (YYYY-MM-DD), and the amount you're claiming.
              </p>
            </div>

            {error && (
              <p className="font-body-md text-body-md" style={{ color: '#b91c1c' }}>
                {error}
              </p>
            )}

            <div className="flex items-center gap-3">
              <button
                className="px-5 py-2.5 bg-primary-container text-on-primary text-[14px] font-medium rounded-DEFAULT hover:bg-on-primary-fixed-variant transition-colors cursor-pointer disabled:opacity-50"
                type="submit"
                disabled={loading}
              >
                {loading ? 'Checking claim…' : 'Submit claim'}
              </button>
              {loading && (
                <span className="text-[13px] text-on-surface-variant">
                  Extracting details, checking coverage and fraud rules. This takes a few seconds.
                </span>
              )}
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
