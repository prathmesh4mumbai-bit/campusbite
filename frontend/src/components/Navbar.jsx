import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { ROLES, ROLE_HOME, ROLE_LABELS } from '../utils/constants';

const LINKS = {
  [ROLES.CUSTOMER]: [
    { to: '/', label: 'Restaurants', end: true },
    { to: '/orders', label: 'My Orders' },
    { to: '/insights', label: 'AI Insights' },
  ],
  [ROLES.OWNER]: [
    { to: '/owner', label: 'Dashboard', end: true },
    { to: '/owner/orders', label: 'Orders' },
    { to: '/owner/menu', label: 'Menu' },
  ],
  [ROLES.DELIVERY]: [{ to: '/delivery', label: 'Deliveries', end: true }],
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const close = () => setOpen(false);
  const handleLogout = () => {
    close();
    logout();
    navigate('/login');
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to={user ? ROLE_HOME[user.role] : '/login'} className="brand" onClick={close}>
          <span aria-hidden="true">{'🍔'}</span> CampusBite
        </Link>

        {user && (
          <>
            <button
              type="button"
              className="nav-toggle"
              aria-label="Toggle menu"
              aria-expanded={open}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? '✕' : '☰'}
            </button>
            <nav className={`nav-links ${open ? 'open' : ''}`}>
              {LINKS[user.role]?.map((link) => (
                <NavLink key={link.to} to={link.to} end={link.end} onClick={close}>
                  {link.label}
                </NavLink>
              ))}
              {user.role === ROLES.CUSTOMER && (
                <NavLink to="/cart" onClick={close}>
                  Cart{count > 0 && <span className="cart-count">{count}</span>}
                </NavLink>
              )}
              <span className="nav-user">
                {user.name} <small>({ROLE_LABELS[user.role]})</small>
              </span>
              <button type="button" className="btn btn-small btn-ghost" onClick={handleLogout}>
                Log out
              </button>
            </nav>
          </>
        )}
      </div>
    </header>
  );
}
