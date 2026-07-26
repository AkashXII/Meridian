import React, { useState } from 'react';

export default function Login({ authToken, setAuthToken }) {
  const [tab, setTab] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (tab === 'register') {
        const res = await fetch('http://localhost:8000/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed');
      }

      // /login expects form-encoded data specifically, not JSON — a FastAPI
      // OAuth2PasswordRequestForm requirement, not something we chose.
      const res = await fetch('http://localhost:8000/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');

      setAuthToken(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-surface-container-lowest">
      <div className="flex-grow flex items-center justify-center p-4">
        <main className="w-full max-w-[400px]">
          <div className="mb-stack-lg text-center">
            <h1 className="font-display-lg text-display-lg text-primary">ClaimsPortal</h1>
          </div>

          <div className="border border-outline-variant bg-surface-container-lowest">
            <div className="flex border-b border-outline-variant">
              <button
                type="button"
                onClick={() => setTab('login')}
                className={`flex-1 py-stack-md text-center font-label-md text-label-md bg-surface-container-lowest cursor-pointer ${
                  tab === 'login'
                    ? 'border-b-2 border-primary text-primary'
                    : 'text-on-surface-variant hover:text-primary transition-colors'
                }`}
              >
                LOG IN
              </button>
              <button
                type="button"
                onClick={() => setTab('register')}
                className={`flex-1 py-stack-md text-center font-label-md text-label-md bg-surface-container-lowest cursor-pointer ${
                  tab === 'register'
                    ? 'border-b-2 border-primary text-primary'
                    : 'text-on-surface-variant hover:text-primary transition-colors'
                }`}
              >
                REGISTER
              </button>
            </div>

            <form className="p-stack-lg" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-stack-lg">
                <div>
                  <label className="block font-label-md text-label-md text-on-surface mb-stack-sm uppercase tracking-wider" htmlFor="email">
                    Email Address
                  </label>
                  <input
                    className="w-full border border-outline-variant p-stack-sm font-body-md text-body-md bg-surface-container-lowest text-on-surface transition-colors"
                    id="email"
                    placeholder="name@company.com"
                    required
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div>
                  <label className="block font-label-md text-label-md text-on-surface mb-stack-sm uppercase tracking-wider" htmlFor="password">
                    Password
                  </label>
                  <input
                    className="w-full border border-outline-variant p-stack-sm font-body-md text-body-md bg-surface-container-lowest text-on-surface transition-colors"
                    id="password"
                    required
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                {error && (
                  <p className="font-body-md text-body-md" style={{ color: '#9B1C1C' }}>{error}</p>
                )}

                <button
                  className="w-full mt-stack-sm py-stack-sm px-gutter bg-primary-container text-on-primary font-label-md text-label-md hover:bg-primary transition-colors duration-200 cursor-pointer disabled:opacity-50"
                  type="submit"
                  disabled={loading}
                >
                  {loading ? 'PLEASE WAIT...' : tab === 'login' ? 'LOG IN' : 'REQUEST ACCESS'}
                </button>

                {tab === 'register' && (
                  <div className="text-center mt-stack-sm">
                    <p className="font-body-md text-body-md text-on-surface-variant">
                      Your request will be sent to the administrator for approval.
                    </p>
                  </div>
                )}
              </div>
            </form>
          </div>
        </main>
      </div>

      <footer className="w-full bg-surface-container border-t border-outline-variant">

      </footer>
    </div>
  );
}