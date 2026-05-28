# Manuel Client - Installation pas a pas FinOptica

Ce guide est fait pour une personne qui n'a jamais deploye une application.

Objectif: installer et lancer FinOptica chez vous, pas a pas, sans connaissance technique avancee.

---

## 1) Ce que vous allez obtenir

A la fin, vous aurez:
- l'application ouverte dans votre navigateur sur `http://localhost:8000/`
- l'API disponible sur `http://localhost:8000/api/v1`
- la doc technique disponible sur `http://localhost:8000/docs`

---

## 2) Prerequis obligatoires (une seule fois)

### Sur Mac
1. Installer Python 3:
   - Ouvrir [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - Installer la version recommandee.
2. Verifier Python:
   - Ouvrir `Terminal`
   - Taper:
   ```bash
   python3 --version
   ```
   - Vous devez voir une version (ex: `Python 3.9.x` ou plus).

### Sur Windows
1. Installer Python 3 depuis [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
2. Cocher la case **Add Python to PATH** pendant l'installation.
3. Verifier:
   ```bash
   python --version
   ```

### Sur Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y python3 python3-pip
python3 --version
```

---

## 3) Recuperer le projet sur votre machine

Si vous avez deja le dossier `Finops-MAN`, passez a l'etape 4.

Sinon:
1. Copier le dossier du projet sur votre machine.
2. Ouvrir un terminal dans le dossier `Finops-MAN`.

Vous devez voir des fichiers comme:
- `run.sh`
- `backend/`
- `frontend/`
- `readme.md`

---

## 4) Demarrage simple (methode recommandee)

Dans le dossier du projet, lancer:

```bash
chmod +x run.sh
./run.sh
```

Le script va:
1. verifier Python
2. installer les dependances
3. lancer le serveur

Quand vous voyez le serveur demarre, ouvrez votre navigateur:
- Application: [http://localhost:8000/](http://localhost:8000/)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 5) Connexion a l'application

Identifiants par defaut (dev local uniquement):
- utilisateur: `admin`
- mot de passe: `finops2026`

Important:
- En production, changez le mot de passe (section 8).
- Ne pas activer `USE_DEMO_DATA` sauf demo commerciale.
- Ajoutez vos connexions AWS/Azure/GCP dans l'onglet **Parametres** ou importez un CSV.

---

## 6) Arreter / redemarrer l'application

### Arreter
Dans le terminal ou l'application tourne, appuyez sur:
- `CTRL + C`

### Redemarrer
Relancez:
```bash
./run.sh
```

---

## 7) Verification rapide (checklist)

Verifier ces 4 points:
1. `http://localhost:8000/` s'ouvre
2. `http://localhost:8000/docs` s'ouvre
3. Login fonctionne avec `admin / finops2026`
4. Les onglets dashboard affichent des donnees

Si oui, le deploiement local est termine.

---

## 8) Configuration minimale securisee (obligatoire chez un client)

Avant de livrer chez un client, definir ces variables:

- `SECRET_KEY`
- `DEFAULT_ADMIN_USERNAME`
- `DEFAULT_ADMIN_PASSWORD`
- `ALLOWED_ORIGINS`

Exemple Mac/Linux (dans le terminal avant lancement):

```bash
export APP_ENV="production"
export SECRET_KEY="changez-cette-cle-secrete-longue"
export DEFAULT_ADMIN_USERNAME="finops_admin"
export DEFAULT_ADMIN_PASSWORD="mot-de-passe-fort"
export ALLOWED_ORIGINS="http://localhost:8000"
export ALLOW_ANONYMOUS_AUTH="false"
export OPENAI_API_KEY="votre-cle-openai"
./run.sh
```

Sur Windows PowerShell:

```powershell
$env:APP_ENV="production"
$env:SECRET_KEY="changez-cette-cle-secrete-longue"
$env:DEFAULT_ADMIN_USERNAME="finops_admin"
$env:DEFAULT_ADMIN_PASSWORD="mot-de-passe-fort"
$env:ALLOWED_ORIGINS="http://localhost:8000"
$env:ALLOW_ANONYMOUS_AUTH="false"
$env:OPENAI_API_KEY="votre-cle-openai"
.\run.sh
```

---

## 9) Deploiement "chez le client" (niveau debutant)

Pour un premier deploiement client sans complexite:

1. Utiliser une machine dediee (PC ou VM) qui reste allumee.
2. Installer Python 3.
3. Copier le projet `Finops-MAN`.
4. Configurer les variables de securite (section 8).
5. Lancer `./run.sh`.
6. Ouvrir le port `8000` uniquement au reseau interne du client.
7. Verifier depuis un autre poste du reseau:
   - `http://IP_DE_LA_MACHINE:8000/`

Exemple:
- si la machine a l'IP `192.168.1.50`
- URL client: `http://192.168.1.50:8000/`

---

## 10) Depannage (problemes frequents)

### Erreur "python3 not found"
- Python n'est pas installe ou pas dans le PATH.
- Refaire la section 2.

### Erreur de dependances pip
- Lancer:
```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt
./.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Le port 8000 est deja utilise
- Fermer l'autre application qui utilise ce port.
- Ou demarrer sur un autre port:
```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload
```

### La page ne charge pas
- Verifier que le terminal affiche bien `Uvicorn running`.
- Verifier l'URL exacte: `http://localhost:8000/`

---

## 11) Ce qu'il faut faire ensuite (recommande)

Apres ce premier deploiement:
1. Ajouter HTTPS (reverse proxy Nginx).
2. Passer sur PostgreSQL au lieu de SQLite.
3. Mettre l'application en service automatique au demarrage machine.
4. Ajouter sauvegardes quotidiennes de la base.

---

Si vous voulez, je peux aussi vous fournir un **manuel client v2** avec:
- procedure Windows detaillee avec captures de commandes,
- procedure Linux serveur (Ubuntu) avec demarrage automatique,
- checklist de recette client avant mise en production.
