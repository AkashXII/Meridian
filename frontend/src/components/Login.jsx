import React, { useState } from 'react';

export default function Login({ authToken, setAuthToken, setUserRole }) {
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

      const res = await fetch('http://localhost:8000/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');

      setUserRole(data.role || 'user');
      setAuthToken(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    'w-full border border-outline-variant px-3 py-2 font-body-md text-body-md bg-white text-on-surface transition-colors';

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <main className="w-full max-w-[380px]">
        <div className="mb-8">
          <div className="flex items-baseline gap-2">
            <span className="text-[22px] font-semibold tracking-tight text-primary">Meridian</span>
            <span className="text-[13px] text-on-surface-variant">Claims</span>
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Sign in to submit and track insurance claims.
          </p>
        </div>

        <div className="bg-white border border-outline-variant rounded-DEFAULT">
          <div className="flex border-b border-outline-variant">
            {[
              { id: 'login', label: 'Log in' },
              { id: 'register', label: 'Create account' },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`flex-1 py-3 text-[14px] border-b-2 -mb-px cursor-pointer transition-colors ${
                  tab === t.id
                    ? 'border-accent text-primary font-medium'
                    : 'border-transparent text-on-surface-variant hover:text-primary'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <form className="p-6" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-5">
              <div>
                <label className="block font-label-md text-label-md text-on-surface mb-1.5" htmlFor="email">
                  Email
                </label>
                <input
                  className={inputClass}
                  id="email"
                  placeholder="name@company.com"
                  required
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-label-md text-label-md text-on-surface mb-1.5" htmlFor="password">
                  Password
                </label>
                <input
                  className={inputClass}
                  id="password"
                  required
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              {error && (
                <p className="font-body-md text-body-md" style={{ color: '#b91c1c' }}>
                  {error}
                </p>
              )}

              <button
                className="w-full py-2.5 bg-primary-container text-on-primary text-[14px] font-medium rounded-DEFAULT hover:bg-on-primary-fixed-variant transition-colors cursor-pointer disabled:opacity-50"
                type="submit"
                disabled={loading}
              >
                {loading ? 'Please wait…' : tab === 'login' ? 'Log in' : 'Create account'}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
