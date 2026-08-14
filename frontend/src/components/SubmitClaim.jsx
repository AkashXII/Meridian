import React, { useState } from 'react';

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
      <header className="bg-surface-container-lowest border-b border-outline-variant w-full">
        <div className="relative flex items-center w-full px-margin-desktop py-4">
          <div
            className="font-headline-sm text-headline-sm font-bold text-primary cursor-pointer"
            onClick={() => setCurrentScreen('submit')}
          >
            Meridian
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
                currentScreen === 'history'
                  ? 'text-primary border-b-2 border-primary font-bold'
                  : 'text-on-surface-variant hover:text-primary'
              }`}
            >
              Claim History
            </button>

            {userRole === 'reviewer' && (
              <button
                type="button"
                onClick={() => setCurrentScreen('review')}
                className={`font-body-md text-body-md pb-1 cursor-pointer transition-colors duration-150 ${
                  currentScreen === 'review'
                    ? 'text-primary border-b-2 border-primary font-bold'
                    : 'text-on-surface-variant hover:text-primary'
                }`}
              >
                Review Queue
              </button>
            )}
          </nav>

          <button
            type="button"
            onClick={() => setAuthToken(null)}
            className="ml-auto font-body-md text-body-md text-primary cursor-pointer hover:text-on-surface-variant transition-all duration-150"
          >
            Log Out
          </button>
        </div>
      </header>

      <main className="flex-grow w-full max-w-container-max mx-auto px-margin-desktop py-12">
        <div className="max-w-2xl mx-auto">
          <div className="mb-stack-lg">
            <h1 className="font-display-lg text-display-lg text-on-surface mb-stack-sm">
              Submit a Claim
            </h1>

            <p className="font-body-lg text-body-lg text-on-surface-variant">
              Please provide detailed information about your claim to expedite the review process.
            </p>
          </div>

          <form className="space-y-stack-lg" onSubmit={handleSubmit}>
            <div className="flex flex-col space-y-stack-sm">
              <label
                className="font-label-md text-label-md text-on-surface uppercase tracking-wider"
                htmlFor="claim-description"
              >
                Describe your claim
              </label>

              <textarea
                className="w-full bg-surface-container-lowest border border-outline-variant rounded p-4 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary focus:ring-0 resize-y"
                id="claim-description"
                placeholder="Enter claim details here..."
                rows="8"
                value={claimDescription}
                onChange={(e) => setClaimDescription(e.target.value)}
              ></textarea>

              <p className="font-body-md text-body-md text-on-surface-variant text-sm">
                Include policy number, date of incident, and estimated amount.
              </p>
            </div>

            {error && (
              <p
                className="font-body-md text-body-md"
                style={{ color: '#9B1C1C' }}
              >
                {error}
              </p>
            )}

            <div className="pt-stack-md">
              <button
                className="w-full sm:w-auto px-8 py-3 bg-primary-container text-on-primary font-label-md text-label-md rounded hover:bg-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer disabled:opacity-50"
                type="submit"
                disabled={loading}
              >
                {loading ? 'Submitting...' : 'Submit Claim'}
              </button>
            </div>
          </form>
        </div>
      </main>

      <footer className="bg-surface-container w-full border-t border-outline-variant mt-auto"></footer>
    </div>
  );
}