import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ErrorMessage } from '../components/ui';
import { ROLE_HOME } from '../utils/constants';

const SHOW_DEMO = import.meta.env.VITE_SHOW_DEMO_LOGINS === 'true';
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || '';
const DEMO_ACCOUNTS = [
  { label: 'Customer', email: 'customer@campusbite.dev' },
  { label: 'Restaurant owner', email: 'owner1@campusbite.dev' },
  { label: 'Delivery partner', email: 'driver1@campusbite.dev' },
];

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(email.trim(), password); // the redirect happens above once `user` is set
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <h1>Welcome back</h1>
        <p className="muted">Log in to order food, manage your restaurant or handle deliveries.</p>
        <ErrorMessage message={error} />
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? 'Logging in...' : 'Log in'}
        </button>
        <p className="muted center">
          New here? <Link to="/register">Create an account</Link>
        </p>

        {SHOW_DEMO && (
          <div className="demo-box">
            <strong>Demo accounts</strong>
            <div className="demo-buttons">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  className="btn btn-small btn-ghost"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword(DEMO_PASSWORD);
                  }}
                >
                  {account.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
