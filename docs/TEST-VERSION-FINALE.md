# Guide de test — Version finale FinOptica MAN

## Démarrage rapide (recommandé pour premier test)

```bash
cd "/Users/mahersahli/Documents/APP gir/Finops-MAN"
cp .env.example .env
```

Dans `.env`, pour un parcours complet avec données :

```env
USE_DEMO_DATA=true
ALLOW_ANONYMOUS_AUTH=true
APP_ENV=development
```

Puis :

```bash
chmod +x run.sh
./run.sh
```

Ouvrir : **http://localhost:8000**

| Champ | Valeur |
|--------|--------|
| Login | `admin` |
| Mot de passe | `finops2026` |

---

## Parcours de test (15 min)

### 1. Dashboard
- Vérifier cartes coût, économies, efficacité, carbone
- Graphique tendance multi-cloud
- Anomalies listées

### 2. Cost Explorer
- Changer la période (7 / 30 / 45 jours)
- Courbe + répartition providers

### 3. Kubernetes
- Tableau namespaces (dérivé des coûts EKS/GKE/AKS après analyse)

### 4. Recommandations
- Cartes Rightsizing, SavingsPlan, Spot, GPU
- **Dry-run** : `POST /api/v1/optimization/recommendations/{id}/dry-run`
- **Apply** : bouton Appliquer (policy gate si risque High)

### 5. Gouvernance FinOps
- Budgets + barres de progression
- Prévision budgétaire
- Showback (team / env / cost_center)
- **Policy-as-Code** : score conformité
- **Alertes** : bouton Évaluer
- **GPU/IA** : workloads détectés
- **Lancer l'analyse IA FinOps** : pipeline complet

### 6. FinOps Copilot
- Nouvelle discussion + question FinOps

### 7. Paramètres
- Statut plateforme (conformité %, features)
- Connecteurs AWS/Azure/GCP (optionnel)
- Import CSV avec colonnes `team`, `env`, `cost_center`

---

## Mode production (données réelles)

```env
USE_DEMO_DATA=false
ALLOW_ANONYMOUS_AUTH=false
SECRET_KEY=<clé-forte>
DEFAULT_ADMIN_PASSWORD=<mot-de-passe-fort>
```

1. Connecter un cloud ou importer CSV
2. Onglet Gouvernance → **Lancer l'analyse IA FinOps**
3. Vérifier recommandations et alertes

---

## APIs clés (Swagger : http://localhost:8000/docs)

| Domaine | Endpoints |
|---------|-----------|
| Billing | `/billing/summary`, `/trend`, `/forecast`, `/budgets`, `/allocation`, `/gpu`, `/finops/analyze` |
| Optimization | `/optimization/recommendations`, `/dry-run`, `/apply` |
| Policies | `/policies`, `/policies/evaluate` |
| Alerts | `/alerts/rules`, `/alerts/events`, `/alerts/evaluate` |
| Copilot | `/copilot/chat`, `/copilot/rag/reindex` |

---

## Tests automatisés

```bash
./.venv/bin/python -m pytest backend/tests -q
```

Résultat attendu : **tous les tests passent**.

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Port 8000 occupé | `lsof -ti:8000 \| xargs kill -9` puis `./run.sh` |
| Dashboard vide | `USE_DEMO_DATA=true` ou import CSV |
| 401 sur l'UI | Se reconnecter (login modal) |
| Pas de K8s | Lancer analyse FinOps après import/sync |

---

## Livrable de cette version

- Moteur FinOps (anomalies, rightsizing, savings, spot, GPU)
- Budgets & forecast
- Showback / chargeback par tags
- Policy-as-code (5 règles)
- Alertes budget & spikes
- Remédiation dry-run + apply contrôlé
- K8s dérivé des coûts cloud
- UI complète 7 onglets
- 20+ tests pytest
