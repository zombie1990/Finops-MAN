const API = '/api/v1';

export function getToken() {
  return localStorage.getItem('finoptica_token') || '';
}

export function setToken(token) {
  localStorage.setItem('finoptica_token', token);
}

export async function apiFetch(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function login(username, password) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  setToken(data.token);
  return data;
}
