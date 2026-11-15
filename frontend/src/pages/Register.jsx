import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ErrorMessage } from '../components/ui';
import { ROLES, ROLE_HOME, ROLE_LABELS } from '../utils/constants';

export default function Register() {
  const { user, register } = useAuth();
  const [form, setForm] = useState({
    role: ROLES.CUSTOMER,
    name: '',
    email: '',
    password: '',
    phone: '',
    address: '',
    restaurant_name: '',
    cuisine: '',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />;

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  const isOwner = form.role === ROLES.OWNER;

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const payload = {
      role: form.role,
      name: form.name.trim(),
      email: form.email.trim(),
      password: form.password,
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
      ...(isOwner ? { restaurant_name: form.restaurant_name.trim(), cuisine: form.cuisine.trim() || null } : {}),
    };
    try {
      await register(payload);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <h1>Create your account</h1>
        <ErrorMessage message={error} />

        <label>
          I am a
          <select value={form.role} onChange={set('role')}>
            {Object.values(ROLES).map((role) => (
              <option key={role} value={role}>
                {ROLE_LABELS[role]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Full name
          <input value={form.name} onChange={set('name')} required minLength={2} maxLength={120} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={set('email')} required autoComplete="email" />
        </label>
        <label>
          Password <small className="muted">(8-72 characters)</small>
          <input
            type="password"
            value={form.password}
            onChange={set('password')}
            required
            minLength={8}
            maxLength={72}
            autoComplete="new-password"
          />
        </label>
        <label>
          Phone <small className="muted">(optional)</small>
          <input value={form.phone} onChange={set('phone')} maxLength={30} />
        </label>
        <label>
          {form.role === ROLES.CUSTOMER ? 'Default delivery address' : 'Address'} <small className="muted">(optional)</small>
          <input value={form.address} onChange={set('address')} maxLength={500} />
        </label>

        {isOwner && (
          <>
            <label>
              Restaurant name
              <input value={form.restaurant_name} onChange={set('restaurant_name')} required maxLength={150} />
            </label>
            <label>
              Cuisine <small className="muted">(optional)</small>
              <input value={form.cuisine} onChange={set('cuisine')} maxLength={80} />
            </label>
          </>
        )}

        <button className="btn" type="submit" disabled={busy}>
          {busy ? 'Creating account...' : 'Sign up'}
        </button>
        <p className="muted center">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
