import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, clearAuth, getStoredAuth, setUnauthorizedHandler, storeAuth } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => getStoredAuth()); // { token, user } | null

  const logout = useCallback(() => {
    clearAuth();
    setAuth(null);
  }, []);

  const persist = useCallback((data) => {
    const next = { token: data.access_token, user: data.user };
    storeAuth(next);
    setAuth(next);
    return data.user;
  }, []);

  const login = useCallback(async (email, password) => persist(await api.post('/auth/login', { email, password }, { auth: false })), [persist]);
  const register = useCallback(async (payload) => persist(await api.post('/auth/register', payload, { auth: false })), [persist]);

  // Any 401 from a protected call (expired token...) signs the user out.
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  // On app start, make sure the stored token is still valid and the user data is fresh.
  useEffect(() => {
    if (!getStoredAuth()?.token) return;
    api
      .get('/auth/me')
      .then((user) => {
        const next = { token: getStoredAuth()?.token, user };
        if (next.token) {
          storeAuth(next);
          setAuth(next);
        }
      })
      .catch(() => {
        /* 401 is handled by the unauthorized handler; network errors keep the session */
      });
  }, []);

  const value = useMemo(
    () => ({ user: auth?.user || null, token: auth?.token || null, login, register, logout }),
    [auth, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
