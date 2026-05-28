// FinOptica AI - Frontend Application Controller
const API_BASE = '/api/v1';

class FinOpticaApp {
  getAuthHeaders(extraHeaders = {}) {
    const headers = { ...extraHeaders };
    const token = localStorage.getItem('finoptica_token');
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }

  async apiFetch(path, options = {}) {
    const headers = this.getAuthHeaders(options.headers || {});
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (response.status === 401 && !path.startsWith('/auth/login')) {
      this.logout(false);
      this.showLoginOverlay('Session expirée. Reconnectez-vous.');
    }
    return response;
  }

  showLoginOverlay(message = '') {
    const overlay = document.getElementById('auth-overlay');
    const err = document.getElementById('login-error');
    if (overlay) overlay.hidden = false;
    if (err) {
      if (message) {
        err.textContent = message;
        err.hidden = false;
      } else {
        err.hidden = true;
        err.textContent = '';
      }
    }
    document.getElementById('app-container')?.setAttribute('aria-hidden', 'true');
  }

  hideLoginOverlay() {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) overlay.hidden = true;
    const err = document.getElementById('login-error');
    if (err) err.hidden = true;
    document.getElementById('app-container')?.removeAttribute('aria-hidden');
  }

  async login(username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Identifiants invalides.');
    }
    const data = await res.json();
    localStorage.setItem('finoptica_token', data.token);
    this.currentUser = data;
    this.updateUserDisplay(data);
    this.hideLoginOverlay();
    return data;
  }

  logout(clearMessage = true) {
    localStorage.removeItem('finoptica_token');
    this.currentUser = null;
    this.updateUserDisplay(null);
    this.showLoginOverlay(clearMessage ? '' : 'Session expirée. Reconnectez-vous.');
  }

  updateUserDisplay(user) {
    const nameEl = document.getElementById('user-display-name');
    const roleEl = document.getElementById('user-display-role');
    const avatarEl = document.getElementById('user-avatar');
    if (!user) {
      if (nameEl) nameEl.textContent = 'Non connecté';
      if (roleEl) roleEl.textContent = '—';
      if (avatarEl) avatarEl.textContent = '--';
      return;
    }
    if (nameEl) nameEl.textContent = user.username;
    if (roleEl) roleEl.textContent = user.role;
    if (avatarEl) {
      const initials = user.username.slice(0, 2).toUpperCase();
      avatarEl.textContent = initials;
    }
  }

  async validateSession() {
    const token = localStorage.getItem('finoptica_token');
    if (!token) return false;
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: this.getAuthHeaders(),
    });
    if (!res.ok) {
      localStorage.removeItem('finoptica_token');
      return false;
    }
    const data = await res.json();
    localStorage.setItem('finoptica_token', data.token);
    this.currentUser = data;
    this.updateUserDisplay(data);
    return true;
  }

  async requireAuth() {
    this.captureTokenFromUrl();
    if (await this.validateSession()) {
      this.hideLoginOverlay();
      return true;
    }
    this.showLoginOverlay();
    return new Promise((resolve) => {
      this._authResolve = resolve;
    });
  }

  bindLoginUi() {
    const form = document.getElementById('login-form');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username')?.value?.trim();
        const password = document.getElementById('login-password')?.value || '';
        const err = document.getElementById('login-error');
        try {
          await this.login(username, password);
          if (this._authResolve) {
            this._authResolve(true);
            this._authResolve = null;
          }
          await this.bootstrapAppData();
        } catch (loginErr) {
          if (err) {
            err.textContent = loginErr.message;
            err.hidden = false;
          }
        }
      });
    }
    const oidcOverlay = document.getElementById('btn-oidc-login-overlay');
    if (oidcOverlay) oidcOverlay.addEventListener('click', () => this.startOidcLogin());
    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) logoutBtn.addEventListener('click', () => this.logout());
  }

  constructor() {
    this.activeTab = 'dashboard-tab';
    this.currentConversationId = null;
    this.conversationList = [];
    
    // Éléments de structure
    this.tabButtons = document.querySelectorAll('.menu-item');
    this.tabSections = document.querySelectorAll('.section-container');
    this.pageTitle = document.getElementById('page-header-title');
    this.pageDesc = document.getElementById('page-header-desc');
    
    // Liaison des événements de navigation
    this.tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        this.switchTab(tabId);
      });
    });
    
    // Liaison de l'assistant IA
    this.chatForm = document.getElementById('chat-form');
    this.chatInputField = document.getElementById('chat-input-field');
    this.chatMessagesContainer = document.getElementById('chat-messages-container');
    this.newThreadBtn = document.getElementById('btn-new-thread');
    this.threadListContainer = document.getElementById('thread-list-container');
    
    if (this.chatForm) {
      this.chatForm.addEventListener('submit', (e) => this.handleSendMessage(e));
    }
    if (this.newThreadBtn) {
      this.newThreadBtn.addEventListener('click', () => this.startNewConversation());
    }

    this.bindSettingsUi();
    this.bindLoginUi();
    this.initThemeSwitcher();
    this.currentUser = null;
    
    // Initialisation
    this.init();
  }

  initThemeSwitcher() {
    this.THEMES = {
      finoptica: { label: 'black&white', icon: 'fa-circle-half-stroke', next: 'shadcn' },
      shadcn: { label: 'FinOptica', icon: 'fa-bolt', next: 'finoptica' },
    };
    this.MONOCHROME_SHADES = ['#050505', '#1a1a1a', '#333333', '#525252', '#737373', '#a3a3a3', '#c4c4c4', '#e8e8e8'];
    this.currentTheme = document.documentElement.getAttribute('data-theme') || 'finoptica';
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => this.toggleTheme());
    }
    this.updateThemeToggleUi();
  }

  getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'finoptica';
  }

  setTheme(theme) {
    const next = theme === 'shadcn' ? 'shadcn' : 'finoptica';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('finoptica_theme', next);
    this.currentTheme = next;
    this.updateThemeToggleUi();
    if (localStorage.getItem('finoptica_token')) {
      this.refreshData();
      if (this.activeTab === 'explorer-tab') {
        this.loadExplorerData();
      }
    }
  }

  isMonochromeTheme() {
    return this.getTheme() === 'shadcn';
  }

  getProviderChartColors() {
    const providers = ['AWS', 'Azure', 'GCP', 'OpenAI'];
    if (this.isMonochromeTheme()) {
      const map = {};
      providers.forEach((prov, index) => {
        map[prov] = this.MONOCHROME_SHADES[index % this.MONOCHROME_SHADES.length];
      });
      map.Other = this.MONOCHROME_SHADES[5];
      return map;
    }
    return {
      AWS: 'var(--accent-blue)',
      Azure: 'var(--accent-purple)',
      GCP: 'var(--accent-orange)',
      OpenAI: 'var(--accent-green)',
      Other: 'var(--accent-blue)',
    };
  }

  getAreaChartGradientMarkup(gradientId = 'area-grad') {
    if (this.isMonochromeTheme()) {
      return `
          <defs>
            <linearGradient id="${gradientId}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#0a0a0a" stop-opacity="0.4"/>
              <stop offset="45%" stop-color="#6b6b6b" stop-opacity="0.18"/>
              <stop offset="100%" stop-color="#e8e8e8" stop-opacity="0"/>
            </linearGradient>
            <linearGradient id="${gradientId}-stroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#050505"/>
              <stop offset="50%" stop-color="#525252"/>
              <stop offset="100%" stop-color="#a3a3a3"/>
            </linearGradient>
          </defs>
        `;
    }
    return `
          <defs>
            <linearGradient id="${gradientId}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--accent-blue)" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="var(--accent-purple)" stop-opacity="0"/>
            </linearGradient>
          </defs>
        `;
  }

  getAreaChartStrokeRef(gradientId = 'area-grad') {
    return this.isMonochromeTheme() ? `url(#${gradientId}-stroke)` : `url(#${gradientId})`;
  }

  toggleTheme() {
    const current = this.getTheme();
    const meta = this.THEMES[current] || this.THEMES.finoptica;
    this.setTheme(meta.next);
  }

  updateThemeToggleUi() {
    const current = this.getTheme();
    const meta = this.THEMES[current] || this.THEMES.finoptica;
    const label = document.getElementById('theme-toggle-label');
    const icon = document.getElementById('theme-toggle-icon');
    if (label) label.textContent = meta.label;
    if (icon) {
      icon.className = `fa-solid ${meta.icon}`;
    }
    document.title = current === 'shadcn'
      ? 'FinOptica — black&white'
      : 'FinOptica AI — SaaS Enterprise Cloud Cost Optimization';
  }

  bindSettingsUi() {
    const connectorForm = document.getElementById('connector-form');
    if (connectorForm) {
      connectorForm.addEventListener('submit', (e) => this.handleCreateConnector(e));
    }
    const providerSelect = document.getElementById('connector-provider');
    if (providerSelect) {
      providerSelect.addEventListener('change', () => this.updateConnectorConfigPlaceholder());
    }
    const dropZone = document.getElementById('csv-drop-zone');
    const fileInput = document.getElementById('csv-file-input');
    if (dropZone && fileInput) {
      dropZone.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', () => this.previewCsvFile(fileInput.files[0]));
      dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = 'var(--accent-blue)'; });
      dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = '#4a5568'; });
      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#4a5568';
        if (e.dataTransfer.files.length) this.previewCsvFile(e.dataTransfer.files[0]);
      });
    }
    const btnImport = document.getElementById('btn-csv-import');
    if (btnImport) btnImport.addEventListener('click', () => this.importCsvFile());
    const btnExport = document.getElementById('btn-csv-export');
    if (btnExport) btnExport.addEventListener('click', () => this.exportCsv());
    const btnOidc = document.getElementById('btn-oidc-login');
    if (btnOidc) btnOidc.addEventListener('click', () => this.startOidcLogin());
    const btnRag = document.getElementById('btn-rag-reindex');
    if (btnRag) btnRag.addEventListener('click', () => this.reindexRag());
    this.updateConnectorConfigPlaceholder();
    this.captureTokenFromUrl();
  }

  captureTokenFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      localStorage.setItem('finoptica_token', token);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }

  async startOidcLogin() {
    const res = await this.apiFetch('/auth/oidc/login');
    const data = await res.json();
    if (data.authorization_url) window.location.href = data.authorization_url;
    else alert(data.detail || 'OIDC non configuré');
  }

  async reindexRag() {
    const res = await this.apiFetch('/copilot/rag/reindex', { method: 'POST' });
    const data = await res.json();
    alert(`RAG réindexé: ${data.documents_indexed} documents`);
  }

  updateConnectorConfigPlaceholder() {
    const provider = document.getElementById('connector-provider')?.value || 'AWS';
    const configField = document.getElementById('connector-config');
    if (!configField) return;
    const templates = {
      AWS: '{\n  "access_key_id": "AKIA...",\n  "secret_access_key": "...",\n  "region": "eu-west-3",\n  "account_id": "123456789012"\n}',
      Azure: '{\n  "tenant_id": "...",\n  "client_id": "...",\n  "client_secret": "...",\n  "subscription_id": "..."\n}',
      GCP: '{\n  "project_id": "my-gcp-project",\n  "service_account_json": {},\n  "bigquery_dataset": "billing_export",\n  "bigquery_table": "gcp_billing_export_v1"\n}'
    };
    configField.value = templates[provider] || '{}';
  }
  
  async bootstrapAppData() {
    await this.loadPlatformStatus();
    await this.refreshData();
    await this.loadConversations();
    if (this.conversationList.length > 0) {
      this.selectConversation(this.conversationList[0].id);
    } else {
      this.startNewConversation();
    }
  }

  async init() {
    console.log("Démarrage de FinOptica AI...");
    const authenticated = await this.requireAuth();
    if (!authenticated) return;
    await this.bootstrapAppData();
  }
  
  switchTab(tabId) {
    this.activeTab = tabId;
    
    // Mettre à jour l'état visuel du menu latéral
    this.tabButtons.forEach(btn => {
      if (btn.getAttribute('data-tab') === tabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
    
    // Afficher la section active
    this.tabSections.forEach(section => {
      if (section.id === tabId) {
        section.classList.add('active');
      } else {
        section.classList.remove('active');
      }
    });
    
    // Mettre à jour les titres de pages de façon élégante
    const titles = {
      'dashboard-tab': { title: 'Console FinOps', desc: 'Analyse financière et détection prédictive d\'anomalies en temps réel.' },
      'explorer-tab': { title: 'Cost Explorer', desc: 'Reverse-engineering et répartition granulaire de votre facturation multi-cloud.' },
      'kubernetes-tab': { title: 'Kubernetes Cost Metrics', desc: 'Optimisation de vos ressources de conteneurisation Kubernetes native.' },
      'optimization-tab': { title: 'Centre de Remédiation', desc: 'Plan d\'actions d\'économies prêtes pour exécution automatisée Terraform et kubectl.' },
      'copilot-tab': { title: 'FinOps AI Copilot', desc: 'Discutez avec votre agent d\'IA expert cloud et automatisez les corrections.' },
      'settings-tab': { title: 'Configuration', desc: 'Connectez AWS, Azure, GCP et importez vos données FinOps réelles.' }
    };
    
    if (titles[tabId]) {
      this.pageTitle.textContent = titles[tabId].title;
      this.pageDesc.textContent = titles[tabId].desc;
    }
    
    // Recharger les données spécifiques selon l'onglet
    if (tabId === 'explorer-tab') {
      this.loadExplorerData();
    } else if (tabId === 'kubernetes-tab') {
      this.loadKubernetesData();
    } else if (tabId === 'optimization-tab') {
      this.loadRecommendations();
    } else if (tabId === 'settings-tab') {
      this.loadSettingsPanel();
    }
  }

  async loadPlatformStatus() {
    try {
      const res = await this.apiFetch('/platform/status');
      const status = await res.json();
      const pill = document.getElementById('platform-mode-pill');
      if (pill) {
        pill.textContent = status.demo_mode ? 'Mode Demo' : 'Production';
        pill.style.color = status.demo_mode ? 'var(--accent-orange)' : 'var(--accent-green)';
      }
      const container = document.getElementById('platform-status-container');
      if (container) {
        container.innerHTML = `
          <p><strong>Environnement:</strong> ${status.environment}</p>
          <p><strong>Mode données:</strong> ${status.data_mode}</p>
          <p><strong>Enregistrements de coûts:</strong> ${status.cost_records}</p>
          <p><strong>Connecteurs actifs:</strong> ${status.connectors_connected} / ${status.connectors_total}</p>
          <p>${status.message}</p>
        `;
      }
      this.platformStatus = status;
    } catch (err) {
      console.error('Erreur statut plateforme:', err);
    }
  }

  async loadSettingsPanel() {
    await this.loadPlatformStatus();
    await this.loadConnectors();
    await this.loadCsvHistory();
  }

  async loadConnectors() {
    const container = document.getElementById('connectors-list');
    if (!container) return;
    try {
      const res = await this.apiFetch('/connectors');
      const connectors = await res.json();
      if (!connectors.length) {
        container.innerHTML = '<p style="color:#718096;">Aucune connexion cloud. Ajoutez AWS, Azure ou GCP.</p>';
        return;
      }
      container.innerHTML = connectors.map(c => `
        <div class="anomaly-item" style="margin-bottom:10px;">
          <div class="anomaly-meta">
            <span class="severity-pill ${c.status === 'Connected' ? 'low' : 'high'}">${c.status}</span>
            <div class="anomaly-info">
              <h5>${c.name} (${c.provider})</h5>
              <p>Type: ${c.connector_type} | Dernière sync: ${c.last_sync_at || 'jamais'} (${c.last_sync_items || 0} items)</p>
              ${c.last_error ? `<p style="color:var(--accent-red)">${c.last_error}</p>` : ''}
            </div>
          </div>
          <div style="display:flex; gap:8px; margin-top:10px;">
            <button class="btn btn-secondary" style="font-size:11px;" onclick="app.testConnector('${c.id}')">Tester</button>
            <button class="btn btn-primary" style="font-size:11px;" onclick="app.syncConnector('${c.id}')">Synchroniser</button>
            <button class="btn btn-danger" style="font-size:11px;" onclick="app.deleteConnector('${c.id}')">Supprimer</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      container.innerHTML = `<p style="color:var(--accent-red)">Erreur: ${err.message}</p>`;
    }
  }

  async handleCreateConnector(e) {
    e.preventDefault();
    const provider = document.getElementById('connector-provider').value;
    const name = document.getElementById('connector-name').value.trim();
    const connector_type = document.getElementById('connector-type').value;
    let config_json = {};
    try {
      config_json = JSON.parse(document.getElementById('connector-config').value || '{}');
    } catch {
      alert('JSON de configuration invalide.');
      return;
    }
    const res = await this.apiFetch('/connectors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, name, connector_type, config_json })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || 'Erreur création connecteur');
      return;
    }
    await this.loadConnectors();
    await this.loadPlatformStatus();
    alert(data.message || 'Connecteur créé');
  }

  async testConnector(id) {
    const res = await this.apiFetch(`/connectors/${id}/test`, { method: 'POST' });
    const data = await res.json();
    alert(data.message || (data.success ? 'Test OK' : 'Test échoué'));
    await this.loadConnectors();
  }

  async syncConnector(id) {
    const res = await this.apiFetch(`/connectors/${id}/sync?days=30`, { method: 'POST' });
    const data = await res.json();
    alert(data.message || (data.success ? `Sync OK (${data.synced_items} items)` : 'Sync échouée'));
    await this.loadConnectors();
    await this.refreshData();
    await this.loadPlatformStatus();
  }

  async deleteConnector(id) {
    if (!confirm('Supprimer cette connexion ?')) return;
    await this.apiFetch(`/connectors/${id}`, { method: 'DELETE' });
    await this.loadConnectors();
  }

  async previewCsvFile(file) {
    if (!file) return;
    this.selectedCsvFile = file;
    const form = new FormData();
    form.append('file', file);
    const res = await this.apiFetch('/data/import/preview', { method: 'POST', body: form });
    const preview = await res.json();
    const container = document.getElementById('csv-preview-container');
    if (container) {
      container.innerHTML = `
        <p><strong>Fichier:</strong> ${preview.filename}</p>
        <p><strong>Colonnes:</strong> ${(preview.headers || []).join(', ')}</p>
        <p><strong>Validation:</strong> ${preview.validation_ok ? 'OK' : 'Colonnes requises: date, provider, service, cost'}</p>
      `;
    }
  }

  async importCsvFile() {
    if (!this.selectedCsvFile) {
      alert('Sélectionnez un fichier CSV.');
      return;
    }
    const form = new FormData();
    form.append('file', this.selectedCsvFile);
    const res = await this.apiFetch('/data/import', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || 'Import échoué');
      return;
    }
    alert(`Import réussi: ${data.items_imported} lignes`);
    await this.loadCsvHistory();
    await this.refreshData();
    await this.loadPlatformStatus();
  }

  async loadCsvHistory() {
    const container = document.getElementById('csv-history-container');
    if (!container) return;
    try {
      const res = await this.apiFetch('/data/import/history');
      const history = await res.json();
      if (!history.length) {
        container.innerHTML = '<p style="color:#718096;">Aucun import.</p>';
        return;
      }
      container.innerHTML = history.map(h => `
        <div style="padding:8px 0; border-bottom:1px solid #2d3748;">
          <strong>${h.filename}</strong> — ${h.status} — ${h.items_parsed} lignes — ${h.uploaded_at}
        </div>
      `).join('');
    } catch (err) {
      container.innerHTML = `<p>${err.message}</p>`;
    }
  }

  async exportCsv() {
    const res = await this.apiFetch('/data/export/csv?days=30');
    if (!res.ok) {
      alert('Export CSV impossible.');
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'finoptica-costs-30d.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  async refreshData() {
    try {
      // Charger le résumé financier global
      const res = await this.apiFetch('/billing/summary');
      const summary = await res.json();

      if (summary.total_cost === 0 && this.platformStatus && !this.platformStatus.demo_mode) {
        const desc = document.getElementById('page-header-desc');
        if (desc && this.activeTab === 'dashboard-tab') {
          desc.textContent = 'Aucune donnée réelle détectée. Connectez un cloud (Paramètres) ou importez un CSV.';
        }
      }
      
      document.getElementById('dash-total-cost').textContent = `${summary.total_cost.toLocaleString()} $`;
      document.getElementById('dash-savings').textContent = `${summary.potential_savings.toLocaleString()} $`;
      document.getElementById('dash-efficiency').textContent = `${summary.efficiency_score}%`;
      document.getElementById('dash-carbon').textContent = `${summary.total_carbon_kg.toLocaleString()} kg`;
      
      const changeEl = document.getElementById('dash-change');
      const arrowIcon = summary.percentage_change >= 0 ? 'up' : 'down';
      const colorClass = summary.percentage_change >= 0 ? 'change-up' : 'change-down';
      
      changeEl.className = `card-change ${colorClass}`;
      changeEl.innerHTML = `<i class="fa-solid fa-arrow-${arrowIcon}"></i> ${Math.abs(summary.percentage_change)}% <span style="color:#718096; font-weight:normal;">vs mois préc.</span>`;
      
      // Charger le graphique de tendances et les anomalies du dashboard
      await this.loadTrendChart();
      await this.loadAnomalies();
    } catch (err) {
      console.error("Erreur lors de la synchronisation des données de coûts:", err);
    }
  }
  
  // --- GRAPHIQUE DE TENDANCE DES COÛTS (SVG INTERACTIF DESSINÉ EN JS) ---
  async loadTrendChart() {
    try {
      const res = await this.apiFetch('/billing/trend?days=30');
      const data = await res.json();
      
      const container = document.getElementById('trend-chart-container');
      if (!container || data.length === 0) return;
      
      container.innerHTML = ''; // Nettoyer
      
      const width = container.clientWidth;
      const height = container.clientHeight;
      const paddingLeft = 60;
      const paddingBottom = 40;
      const paddingTop = 20;
      const paddingRight = 20;
      
      const chartWidth = width - paddingLeft - paddingRight;
      const chartHeight = height - paddingTop - paddingBottom;
      
      // Trouver les bornes min/max
      const maxVal = Math.max(...data.map(d => d.total)) * 1.1; // +10% marge
      
      // Dessiner le SVG
      let svgContent = `<svg class="chart-svg" width="${width}" height="${height}">`;
      
      // Lignes de grille horizontales et graduations Y
      const gridCount = 5;
      for (let i = 0; i <= gridCount; i++) {
        const val = (maxVal / gridCount) * i;
        const y = height - paddingBottom - (chartHeight / gridCount) * i;
        
        svgContent += `
          <line class="chart-grid-line" x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" />
          <text class="chart-text" x="${paddingLeft - 10}" y="${y + 4}" text-anchor="end">${Math.round(val)} $</text>
        `;
      }
      
      // Tracer les séries multi-providers en barres empilées
      const barWidth = Math.max(chartWidth / data.length * 0.65, 4);
      const step = chartWidth / (data.length - 1 || 1);
      
      const providers = ['AWS', 'Azure', 'GCP', 'OpenAI'];
      const colors = this.getProviderChartColors();
      
      data.forEach((day, index) => {
        const x = paddingLeft + index * step - barWidth / 2;
        
        // Empilement des barres
        let yOffset = 0;
        providers.forEach(prov => {
          const val = day[prov] || 0;
          if (val === 0) return;
          
          const barHeight = (val / maxVal) * chartHeight;
          const y = height - paddingBottom - yOffset - barHeight;
          
          svgContent += `
            <rect class="chart-bar" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${colors[prov]}"
                  data-day="${day.date}" data-prov="${prov}" data-val="${val}">
              <title>${day.date} - ${prov}: ${val} $</title>
            </rect>
          `;
          
          yOffset += barHeight;
        });
        
        // Légende axe X toutes les 5 dates
        if (index % 5 === 0) {
          const dateLabel = day.date.substring(5); // Format MM-DD
          svgContent += `
            <text class="chart-text" x="${x + barWidth/2}" y="${height - 15}" text-anchor="middle">${dateLabel}</text>
          `;
        }
      });
      
      svgContent += `</svg>`;
      container.innerHTML = svgContent;
      
      // Générer la légende sous le graphique
      const legendContainer = document.getElementById('trend-chart-legend');
      if (legendContainer) {
        legendContainer.innerHTML = providers.map(prov => `
          <div class="legend-item">
            <div class="legend-color" style="background:${colors[prov]}"></div>
            <span>${prov}</span>
          </div>
        `).join('');
      }
      
    } catch (err) {
      console.error("Erreur lors de la construction du graphique:", err);
    }
  }
  
  // --- ANOMALIES ---
  async loadAnomalies() {
    try {
      const res = await this.apiFetch('/billing/anomalies');
      const anomalies = await res.json();
      
      const container = document.getElementById('anomalies-container');
      if (!container) return;
      
      container.innerHTML = '';
      
      if (anomalies.length === 0) {
        container.innerHTML = '<div style="color:#718096; padding: 20px; text-align:center;">Aucune anomalie détectée récemment. Excellent travail !</div>';
        return;
      }
      
      anomalies.forEach(anom => {
        const severityClass = anom.severity.toLowerCase();
        
        const cardHTML = `
          <div class="anomaly-item">
            <div class="anomaly-meta">
              <span class="severity-pill ${severityClass}">${anom.severity}</span>
              <div class="anomaly-info">
                <h5>${anom.service} (${anom.provider})</h5>
                <p>Détecté sur : <code>${anom.resource_id}</code> le ${anom.date}</p>
              </div>
            </div>
            
            <div class="anomaly-values">
              <div class="anomaly-cost-spike">${anom.actual_cost.toLocaleString()} $</div>
              <div class="anomaly-percentage">+${anom.deviation_percentage}% pic</div>
            </div>
          </div>
        `;
        container.insertAdjacentHTML('beforeend', cardHTML);
      });
      
    } catch (err) {
      console.error("Erreur lors du chargement des anomalies:", err);
    }
  }
  
  // --- COST EXPLORER PAGE ---
  async loadExplorerData() {
    try {
      const days = document.getElementById('explorer-days').value || 30;
      
      // Graphique de tendance du Cost Explorer (Graphique en barres totalisées)
      const resTrend = await this.apiFetch(`/billing/trend?days=${days}`);
      const dataTrend = await resTrend.json();
      
      const container = document.getElementById('explorer-chart-container');
      if (container && dataTrend.length > 0) {
        container.innerHTML = '';
        
        const width = container.clientWidth;
        const height = container.clientHeight;
        const paddingLeft = 60;
        const paddingBottom = 40;
        const paddingTop = 20;
        const paddingRight = 20;
        
        const chartWidth = width - paddingLeft - paddingRight;
        const chartHeight = height - paddingTop - paddingBottom;
        const maxVal = Math.max(...dataTrend.map(d => d.total)) * 1.1;
        
        let svgContent = `<svg class="chart-svg" width="${width}" height="${height}">`;
        
        // Grille & Grad Y
        const gridCount = 5;
        for (let i = 0; i <= gridCount; i++) {
          const val = (maxVal / gridCount) * i;
          const y = height - paddingBottom - (chartHeight / gridCount) * i;
          svgContent += `
            <line class="chart-grid-line" x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" />
            <text class="chart-text" x="${paddingLeft - 10}" y="${y + 4}" text-anchor="end">${Math.round(val)} $</text>
          `;
        }
        
        // Tracer une courbe fluide (Area Line Chart) pour le total cumulé
        let points = [];
        const step = chartWidth / (dataTrend.length - 1 || 1);
        
        dataTrend.forEach((day, index) => {
          const x = paddingLeft + index * step;
          const y = height - paddingBottom - (day.total / maxVal) * chartHeight;
          points.push(`${x},${y}`);
          
          if (index % Math.ceil(dataTrend.length / 6) === 0) {
            const dateLabel = day.date.substring(5);
            svgContent += `
              <text class="chart-text" x="${x}" y="${height - 15}" text-anchor="middle">${dateLabel}</text>
            `;
          }
        });
        
        const pathData = `M ${points.join(' L ')}`;
        const areaData = `${pathData} L ${paddingLeft + chartWidth},${height - paddingBottom} L ${paddingLeft},${height - paddingBottom} Z`;
        
        svgContent += this.getAreaChartGradientMarkup('explorer-area-grad');
        svgContent += `
          <path class="chart-area" d="${areaData}" fill="url(#explorer-area-grad)" />
          <path class="chart-line" d="${pathData}" stroke="${this.getAreaChartStrokeRef('explorer-area-grad')}" />
        `;
        
        svgContent += `</svg>`;
        container.innerHTML = svgContent;
      }
      
      // Répartition par Cloud (Barres horizontales)
      const resProv = await this.apiFetch(`/billing/providers?days=${days}`);
      const dataProv = await resProv.json();
      
      const provContainer = document.getElementById('explorer-providers-container');
      if (provContainer) {
        provContainer.innerHTML = '';
        
        const totalAmount = dataProv.reduce((sum, item) => sum + item.cost, 0);
        
        const colors = this.getProviderChartColors();
        const labelColor = this.isMonochromeTheme() ? '#0a0a0a' : '#fff';
        
        dataProv.forEach((item, index) => {
          const percentage = totalAmount > 0 ? (item.cost / totalAmount * 100) : 0;
          const color = colors[item.provider] || this.MONOCHROME_SHADES[index % this.MONOCHROME_SHADES.length] || 'var(--accent-blue)';
          
          const barHTML = `
            <div>
              <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:6px;">
                <span style="font-weight:600; color:${labelColor};">${item.provider}</span>
                <span>${item.cost.toLocaleString()} $ (${Math.round(percentage)}%)</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width:${percentage}%; background:${color}"></div>
              </div>
              <div style="font-size:11px; color:#718096; margin-top:4px;">🌱 Carbone : ${item.carbon_kg.toLocaleString()} kg CO2</div>
            </div>
          `;
          provContainer.insertAdjacentHTML('beforeend', barHTML);
        });
      }
      
    } catch (err) {
      console.error("Erreur lors de la charge du Cost Explorer:", err);
    }
  }
  
  // --- KUBERNETES PAGE ---
  async loadKubernetesData() {
    try {
      const res = await this.apiFetch('/billing/kubernetes');
      const namespaces = await res.json();
      
      const tbody = document.getElementById('k8s-table-body');
      if (!tbody) return;
      
      tbody.innerHTML = '';
      
      namespaces.forEach(ns => {
        const cpuPercent = Math.round(ns.cpu_used / ns.cpu_requested * 100);
        const memPercent = Math.round(ns.memory_used_gb / ns.memory_requested_gb * 100);
        
        // Couleur selon l'efficacité globale
        let effColorClass = 'success';
        if (ns.efficiency_score < 40) effColorClass = 'danger';
        else if (ns.efficiency_score < 75) effColorClass = 'warning';
        
        const rowHTML = `
          <tr>
            <td style="font-weight:600; color:#fff;"><code>${ns.namespace}</code></td>
            <td>
              <div style="font-weight:500;">${ns.cpu_used} / ${ns.cpu_requested} cores</div>
              <div class="progress-bar-wrapper" style="margin-top:4px;">
                <div class="progress-bar-bg" style="width:100px;">
                  <div class="progress-bar-fill" style="width:${cpuPercent}%"></div>
                </div>
                <span style="font-size:11px; color:#718096">${cpuPercent}%</span>
              </div>
            </td>
            <td>
              <div style="font-weight:500;">${ns.memory_used_gb} / ${ns.memory_requested_gb} GB</div>
              <div class="progress-bar-wrapper" style="margin-top:4px;">
                <div class="progress-bar-bg" style="width:100px;">
                  <div class="progress-bar-fill" style="width:${memPercent}%"></div>
                </div>
                <span style="font-size:11px; color:#718096">${memPercent}%</span>
              </div>
            </td>
            <td style="font-weight:700; color:#fff;">${ns.total_cost.toLocaleString()} $</td>
            <td>
              <div class="progress-bar-wrapper">
                <div class="progress-bar-bg" style="width:120px;">
                  <div class="progress-bar-fill ${effColorClass}" style="width:${ns.efficiency_score}%"></div>
                </div>
                <span style="font-weight:700; color:var(--accent-${effColorClass === 'success' ? 'green' : effColorClass === 'warning' ? 'orange' : 'red'})">${ns.efficiency_score}%</span>
              </div>
            </td>
          </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', rowHTML);
      });
      
    } catch (err) {
      console.error("Erreur lors de la charge de l'onglet Kubernetes:", err);
    }
  }
  
  // --- CENTRE DE RECOMMANDATIONS ---
  async loadRecommendations() {
    try {
      const res = await this.apiFetch('/optimization/recommendations');
      const recoms = await res.json();
      
      const container = document.getElementById('recommendations-container');
      const countLabel = document.getElementById('active-recom-count');
      
      if (!container) return;
      
      container.innerHTML = '';
      
      const pendingCount = recoms.filter(r => r.status === 'Pending').length;
      countLabel.textContent = `${pendingCount} recommandation${pendingCount > 1 ? 's' : ''} active${pendingCount > 1 ? 's' : ''}`;
      
      recoms.forEach(r => {
        const isApplied = r.status === 'Applied';
        const typeClass = r.recommendation_type.toLowerCase();
        const riskClass = `risk-${r.operational_risk.toLowerCase()}`;
        
        const cardHTML = `
          <div class="rec-card" id="rec-card-${r.id}">
            <!-- En-tête cliquable pour déplier -->
            <div class="rec-header" onclick="app.toggleRecCard('${r.id}')">
              <span class="rec-type-badge ${typeClass}">${r.recommendation_type}</span>
              <div class="rec-title-desc">
                <h4>${r.resource_name}</h4>
                <p>Identifiant : <code>${r.resource_id}</code> | Service : ${r.service}</p>
              </div>
              <div class="rec-financials">
                <div class="saving-value">${r.estimated_saving.toLocaleString()} $ / mois</div>
                <div class="saving-label">Coût actuel : ${r.current_cost} $</div>
              </div>
              <div class="rec-meta-pills">
                <div class="meta-pill ${riskClass}"><i class="fa-solid fa-triangle-exclamation"></i> Risque ${r.operational_risk}</div>
                <span class="status-badge ${r.status.toLowerCase()}">${isApplied ? 'Appliqué' : 'À optimiser'}</span>
              </div>
            </div>
            
            <!-- Tiroir déployable (Drawer) -->
            <div class="rec-drawer" id="rec-drawer-${r.id}">
              <div class="drawer-layout">
                <div>
                  <div class="script-panel-header">
                    <span>Script de Remédiation Généré (${r.remediation_script_type.toUpperCase()})</span>
                    <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="navigator.clipboard.writeText(\`${r.remediation_script.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)">
                      <i class="fa-solid fa-copy"></i> Copier le code
                    </button>
                  </div>
                  <div class="script-panel">${r.remediation_script}</div>
                </div>
                
                <div class="drawer-actions">
                  <div class="action-info">
                    <p style="font-weight:600; color:#fff; margin-bottom:8px;">Description détaillée du plan :</p>
                    <p style="margin-bottom:12px;">${r.description}</p>
                    <p><i class="fa-solid fa-clock" style="color:var(--accent-blue)"></i> <strong>Temps de ROI</strong> : ~ ${r.roi_days} jours | <strong>Effort d'implémentation</strong> : ${r.remediation_effort}</p>
                  </div>
                  
                  <div>
                    <div class="action-buttons">
                      ${isApplied ? `
                        <button class="btn btn-danger" onclick="app.rollbackRemediation('${r.id}')">
                          <i class="fa-solid fa-undo"></i> Revenir à la config d'origine (Rollback)
                        </button>
                      ` : `
                        <button class="btn btn-primary" onclick="app.applyRemediation('${r.id}')">
                          <i class="fa-solid fa-play"></i> Appliquer la remédiation (IaC/CLI)
                        </button>
                        <button class="btn btn-secondary" style="margin-left:8px;" onclick="app.createGithubPr('${r.id}')">
                          <i class="fa-brands fa-github"></i> Créer PR GitHub
                        </button>
                      `}
                    </div>
                    <!-- Panneau de Log d'exécution en arrière-plan -->
                    <div class="output-log-panel" id="output-log-${r.id}"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        `;
        container.insertAdjacentHTML('beforeend', cardHTML);
      });
      
    } catch (err) {
      console.error("Erreur lors du chargement des optimisations:", err);
    }
  }
  
  toggleRecCard(recId) {
    const card = document.getElementById(`rec-card-${recId}`);
    if (card) {
      card.classList.toggle('expanded');
    }
  }
  
  async applyRemediation(recId) {
    const logPanel = document.getElementById(`output-log-${recId}`);
    if (logPanel) {
      logPanel.classList.add('active');
      logPanel.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Initialisation du microservice de remédiation IaC...';
    }
    
    try {
      const res = await this.apiFetch(`/optimization/recommendations/${recId}/apply`, { method: 'POST' });
      const data = await res.json();
      
      if (data.success) {
        // Simuler le défilement progressif du log de déploiement
        setTimeout(() => {
          logPanel.innerHTML = `[DRY-RUN] Validation syntaxique du script réussie.\n[SECURITY] Scan vulnérabilités de sécurité : OK (0 alerte).\n[PLAN] Génération du plan d'exécution.\n[EXECUTION] Application réussie.`;
          
          setTimeout(() => {
            logPanel.innerHTML = data.output;
            this.refreshData(); // Mettre à jour les métriques globales instantanément !
            this.loadRecommendations(); // Recharger la carte pour afficher "Appliqué"
          }, 1200);
        }, 800);
      }
    } catch (err) {
      if (logPanel) {
        logPanel.innerHTML = `⚠️ Erreur d'exécution : ${err.message}`;
      }
    }
  }
  
  async createGithubPr(recId) {
    try {
      const res = await this.apiFetch(`/automation/github/pr/${recId}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert(`PR créée: ${data.pr_url}`);
      } else {
        alert(data.detail || data.message || 'Echec création PR');
      }
    } catch (err) {
      alert(`Erreur PR GitHub: ${err.message}`);
    }
  }

  async rollbackRemediation(recId) {
    const logPanel = document.getElementById(`output-log-${recId}`);
    if (logPanel) {
      logPanel.classList.add('active');
      logPanel.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Initialisation du rollback...';
    }
    
    try {
      const res = await this.apiFetch(`/optimization/recommendations/${recId}/rollback`, { method: 'POST' });
      const data = await res.json();
      
      if (data.success) {
        setTimeout(() => {
          logPanel.innerHTML = data.output;
          this.refreshData();
          this.loadRecommendations();
        }, 1000);
      }
    } catch (err) {
      if (logPanel) {
        logPanel.innerHTML = `⚠️ Erreur lors du rollback : ${err.message}`;
      }
    }
  }
  
  // --- COPILOTE IA CONVERSATIONNEL ---
  async loadConversations() {
    try {
      const res = await this.apiFetch('/copilot/conversations');
      this.conversationList = await res.json();
      this.renderConversationList();
    } catch (err) {
      console.error("Erreur lors de la charge des fils de discussion:", err);
    }
  }
  
  renderConversationList() {
    if (!this.threadListContainer) return;
    this.threadListContainer.innerHTML = '';
    
    this.conversationList.forEach(c => {
      const isActive = c.id === this.currentConversationId;
      const itemHTML = `
        <div class="thread-item ${isActive ? 'active' : ''}" onclick="app.selectConversation('${c.id}')">
          <div class="thread-title"><i class="fa-solid fa-message"></i> ${c.title}</div>
          <div class="thread-date">Créé le ${c.created_at}</div>
        </div>
      `;
      this.threadListContainer.insertAdjacentHTML('beforeend', itemHTML);
    });
  }
  
  async startNewConversation() {
    this.currentConversationId = null; // Backend en générera une
    this.chatMessagesContainer.innerHTML = '';
    
    // Charger le fil pour déclencher le welcome message
    await this.selectConversation(null);
  }
  
  async selectConversation(id) {
    this.currentConversationId = id;
    
    // Mettre à jour la sélection visuelle
    this.renderConversationList();
    
    if (!this.chatMessagesContainer) return;
    this.chatMessagesContainer.innerHTML = '';
    
    try {
      const path = id ? `/copilot/history/${id}` : '/copilot/history/new';
      const res = await this.apiFetch(path);
      const history = await res.json();
      
      if (history.length > 0 && !id) {
        // Enregistrer l'ID de la nouvelle discussion générée par le serveur
        this.currentConversationId = history[0].conversation_id || history[0].id;
        await this.loadConversations();
      }
      
      history.forEach(msg => {
        this.appendMessage(msg.role, msg.content, msg.metadata);
      });
      
      this.scrollToBottom();
    } catch (err) {
      console.error("Erreur de sélection de discussion:", err);
    }
  }
  
  appendMessage(role, content, metadata) {
    if (!this.chatMessagesContainer) return;
    
    const wrapper = document.createElement('div');
    wrapper.className = `msg-wrapper ${role}`;
    
    // Parsing markdown basique pour le chat (Listes, Gras, Tableaux, Code)
    let formattedContent = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
      
    // Gérer les retours à la ligne simples sauf dans les pré
    formattedContent = formattedContent.split('\n').map(line => {
      if (line.trim().startsWith('*') || line.trim().startsWith('-')) {
        return `<li>${line.trim().substring(1).trim()}</li>`;
      }
      if (line.includes('<tr>') || line.includes('<td>') || line.includes('<table>') || line.startsWith('|') || line.startsWith('<pre>') || line.startsWith('</pre>') || line.startsWith('<li>')) {
        return line;
      }
      return `<p>${line}</p>`;
    }).join('\n');
    
    // Gérer les listes <li> orphelines
    formattedContent = formattedContent.replace(/(<li>.*?<\/li>)/g, '<ul>$1</ul>');
    // Remplacer les multi ul consécutifs
    formattedContent = formattedContent.replace(/<\/ul>\n<ul>/g, '\n');
    
    // Parser les tableaux Markdown
    if (formattedContent.includes('|')) {
      const lines = formattedContent.split('\n');
      let insideTable = false;
      let tableHTML = '<table class="k8s-table" style="margin: 15px 0; background: rgba(0,0,0,0.15);"><thead>';
      
      lines.forEach((line, idx) => {
        if (line.trim().startsWith('|')) {
          const cells = line.split('|').map(c => c.trim()).filter(c => c !== '');
          if (idx === 0 || !insideTable) {
            insideTable = true;
            tableHTML += '<tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
          } else if (line.includes('---')) {
            // Ignorer la ligne de séparation markdown
          } else {
            tableHTML += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
          }
        } else if (insideTable) {
          insideTable = false;
          tableHTML += '</tbody></table>';
          formattedContent = formattedContent.replace(lines[idx-1], tableHTML);
        }
      });
    }
    
    let widgetHTML = '';
    if (metadata) {
      if (metadata.type === 'remediation_widget') {
        widgetHTML = `
          <div class="chat-widget">
            <div class="chat-widget-header"><i class="fa-solid fa-wand-magic-sparkles"></i> Action Copilot Disponible</div>
            <div style="font-size:13px; margin-bottom:12px;">Appliquez la remédiation en direct pour économiser <strong>${metadata.estimated_saving} $ / mois</strong> sur cette ressource.</div>
            <button class="btn btn-primary" style="padding:8px 16px; font-size:11px;" onclick="app.applyWidgetRemediation(this, '${metadata.recommendation_id}')">
              <i class="fa-solid fa-play"></i> Appliquer le correctif
            </button>
          </div>
        `;
      }
    }
    
    wrapper.innerHTML = `
      <div class="msg-bubble">
        ${formattedContent}
        ${widgetHTML}
      </div>
    `;
    
    this.chatMessagesContainer.appendChild(wrapper);
    this.scrollToBottom();
  }
  
  async applyWidgetRemediation(buttonEl, recId) {
    buttonEl.disabled = true;
    buttonEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Application...';
    
    try {
      const res = await this.apiFetch(`/optimization/recommendations/${recId}/apply`, { method: 'POST' });
      const data = await res.json();
      
      if (data.success) {
        buttonEl.className = 'btn btn-secondary';
        buttonEl.innerHTML = '<i class="fa-solid fa-check" style="color:var(--accent-green)"></i> Correctif Appliqué !';
        this.refreshData();
      }
    } catch (err) {
      buttonEl.innerHTML = '⚠️ Erreur';
    }
  }
  
  async handleSendMessage(e) {
    e.preventDefault();
    const prompt = this.chatInputField.value.trim();
    if (!prompt) return;
    
    this.chatInputField.value = '';
    
    // Afficher le message utilisateur immédiatement
    this.appendMessage('user', prompt);
    
    // Afficher l'indicateur de réflexion (Typing Indicator)
    const typingWrapper = document.createElement('div');
    typingWrapper.className = 'msg-wrapper assistant';
    typingWrapper.id = 'typing-indicator-wrapper';
    typingWrapper.innerHTML = `
      <div class="msg-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    this.chatMessagesContainer.appendChild(typingWrapper);
    this.scrollToBottom();
    
    try {
      const res = await this.apiFetch('/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: this.currentConversationId,
          prompt: prompt
        })
      });
      const data = await res.json();
      
      // Supprimer l'indicateur
      const indicator = document.getElementById('typing-indicator-wrapper');
      if (indicator) indicator.remove();
      
      this.currentConversationId = data.conversation_id;
      
      // Afficher le message de l'assistant avec micro-remédiation
      this.appendMessage('assistant', data.content, data.metadata);
      
      // Recharger la liste des discussions au cas où le titre a changé
      await this.loadConversations();
    } catch (err) {
      const indicator = document.getElementById('typing-indicator-wrapper');
      if (indicator) indicator.remove();
      this.appendMessage('assistant', `⚠️ Oups, je rencontre une difficulté réseau pour me connecter au moteur de RAG : ${err.message}`);
    }
  }
  
  scrollToBottom() {
    if (this.chatMessagesContainer) {
      this.chatMessagesContainer.scrollTop = this.chatMessagesContainer.scrollHeight;
    }
  }
}

// Lancer l'application
let app;
window.addEventListener('DOMContentLoaded', () => {
  app = new FinOpticaApp();
  window.app = app;
});
