// Thin wrapper around fetch(): base URL, JSON, JWT header, and friendly errors.

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const AUTH_KEY = 'campusbite_auth';

let unauthorizedHandler = null;
export const setUnauthorizedHandler = (fn) => {
  unauthorizedHandler = fn;
};

export class ApiError extends Error {
  constructor(message, status, retryAfter = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

// ----- token + user persisted in localStorage -----
export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
export const storeAuth = (auth) => localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
export const clearAuth = () => localStorage.removeItem(AUTH_KEY);

function buildUrl(path, params) {
  const url = new URL(BASE_URL + path);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  return url.toString();
}

function extractMessage(data, fallback) {
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc.filter((p) => p !== 'body').join('.') : '';
        const msg = (d.msg || 'Invalid value').replace(/^Value error, /, '');
        return field ? `${field}: ${msg}` : msg;
      })
      .join('; ');
  }
  return fallback || 'Something went wrong';
}

async function request(method, path, { body, params, auth = true } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const stored = getStoredAuth();
  if (auth && stored?.token) headers.Authorization = `Bearer ${stored.token}`;

  let response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Cannot reach the server. Please check your connection and try again.', 0);
  }

  if (response.status === 204) return null;

  let data = null;
  try {
    data = await response.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (!response.ok) {
    // An expired / invalid token on a protected call: sign the user out.
    if (response.status === 401 && auth && stored?.token && unauthorizedHandler) unauthorizedHandler();
    throw new ApiError(extractMessage(data, response.statusText), response.status, response.headers.get('Retry-After'));
  }
  return data;
}

export const api = {
  get: (path, params) => request('GET', path, { params }),
  post: (path, body, opts = {}) => request('POST', path, { body: body ?? {}, ...opts }),
  put: (path, body) => request('PUT', path, { body }),
  patch: (path, body) => request('PATCH', path, { body }),
  delete: (path) => request('DELETE', path),
};
