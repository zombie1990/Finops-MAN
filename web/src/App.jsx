import { useEffect, useState } from 'react';
import { Link, Route, Routes, useNavigate } from 'react-router-dom';
import { apiFetch, getToken, login, setToken } from './api';

function LoginPage() {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('finops2026');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={onSubmit} className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-xl p-8 space-y-4">
        <h1 className="text-2xl font-bold">FinOptica Enterprise</h1>
        <p className="text-slate-400 text-sm">Connexion production (données réelles)</p>
        <input className="w-full p-3 rounded bg-slate-800 border border-slate-700" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Utilisateur" />
        <input className="w-full p-3 rounded bg-slate-800 border border-slate-700" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Mot de passe" />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button className="w-full py-3 rounded bg-blue-600 hover:bg-blue-500 font-semibold">Se connecter</button>
        <a href="/api/v1/auth/oidc/login" className="block text-center text-sm text-blue-400">SSO OIDC (Azure AD / Okta)</a>
      </form>
    </div>
  );
}

function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    apiFetch('/billing/summary').then(setSummary).catch(console.error);
    apiFetch('/platform/status').then(setStatus).catch(console.error);
  }, []);

  return (
    <div className="p-8 space-y-6">
      <h2 className="text-3xl font-bold">Dashboard FinOps</h2>
      {status && (
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 text-sm">
          Mode: <strong>{status.data_mode}</strong> | Coûts: {status.cost_records} | Connecteurs: {status.connectors_connected}/{status.connectors_total}
        </div>
      )}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <Card label="Coût total" value={`${summary.total_cost} $`} />
          <Card label="Économies" value={`${summary.potential_savings} $`} />
          <Card label="Efficacité" value={`${summary.efficiency_score}%`} />
          <Card label="Carbone" value={`${summary.total_carbon_kg} kg`} />
        </div>
      )}
    </div>
  );
}

function SettingsPage() {
  const [connectors, setConnectors] = useState([]);
  const [provider, setProvider] = useState('AWS');
  const [name, setName] = useState('');
  const [config, setConfig] = useState('{}');

  async function load() {
    setConnectors(await apiFetch('/connectors'));
  }

  useEffect(() => { load(); }, []);

  async function addConnector(e) {
    e.preventDefault();
    await apiFetch('/connectors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider,
        name,
        connector_type: 'billing_api',
        config_json: JSON.parse(config),
      }),
    });
    await load();
  }

  async function sync(id) {
    await apiFetch(`/connectors/${id}/sync?days=30`, { method: 'POST' });
    await load();
  }

  return (
    <div className="p-8 space-y-6">
      <h2 className="text-2xl font-bold">Configuration Cloud</h2>
      <form onSubmit={addConnector} className="bg-slate-900 border border-slate-700 rounded-lg p-4 space-y-3 max-w-2xl">
        <select value={provider} onChange={(e) => setProvider(e.target.value)} className="w-full p-2 rounded bg-slate-800">
          <option>AWS</option><option>Azure</option><option>GCP</option>
        </select>
        <input className="w-full p-2 rounded bg-slate-800" placeholder="Nom connexion" value={name} onChange={(e) => setName(e.target.value)} />
        <textarea className="w-full p-2 rounded bg-slate-800 h-32 font-mono text-xs" value={config} onChange={(e) => setConfig(e.target.value)} />
        <button className="px-4 py-2 bg-blue-600 rounded">Ajouter</button>
      </form>
      <div className="space-y-2">
        {connectors.map((c) => (
          <div key={c.id} className="flex justify-between items-center bg-slate-900 border border-slate-700 rounded p-3">
            <div>
              <strong>{c.name}</strong> ({c.provider}) — {c.status}
              {c.last_error && <p className="text-red-400 text-xs">{c.last_error}</p>}
            </div>
            <button onClick={() => sync(c.id)} className="px-3 py-1 bg-emerald-600 rounded text-sm">Sync</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function Card({ label, value }) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
      <p className="text-xs text-slate-400 uppercase">{label}</p>
      <p className="text-2xl font-bold mt-2">{value}</p>
    </div>
  );
}

function Shell({ children }) {
  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-slate-900 border-r border-slate-800 p-4 space-y-2">
        <p className="font-bold text-lg mb-4">FinOptica</p>
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/settings">Paramètres</NavLink>
      </aside>
      <main className="flex-1">{children}</main>
    </div>
  );
}

function NavLink({ to, children }) {
  return <Link to={to} className="block px-3 py-2 rounded hover:bg-slate-800 text-slate-300">{children}</Link>;
}

function Protected({ children }) {
  return getToken() ? children : <LoginPage />;
}

export default function App() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      setToken(token);
      window.history.replaceState({}, '', '/dashboard');
    }
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<Protected><Shell><DashboardPage /></Shell></Protected>} />
      <Route path="/settings" element={<Protected><Shell><SettingsPage /></Shell></Protected>} />
      <Route path="*" element={<Protected><Shell><DashboardPage /></Shell></Protected>} />
    </Routes>
  );
}
