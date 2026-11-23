# Agent DevOps

Agent IA qui surveille la chaîne de livraison logicielle : il lit les logs d'un pipeline CI/CD,
identifie l'étape fautive, propose un correctif et, selon des règles de sécurité strictes,
peut relancer un job, déclencher un rollback ou ouvrir une PR corrective.

- **Groupe** : voir `docs/equipe.md` — **Sujet n° catalogue** : à compléter
- **Module** : IA et Dev (Exploitation et infrastructure)

## Fonctionnement en bref

`logs -> analyse (règles + abstention) -> explication LLM (optionnelle) -> politique de sécurité -> action ou validation humaine -> journal d'audit`

| Action | Risque | Règle |
| --- | --- | --- |
| Relancer un job | faible | automatique si confiance suffisante et relances limitées |
| Ouvrir une PR | moyen | automatique, jamais fusionnée par l'agent |
| Rollback | élevé | **validation humaine obligatoire** |
| Secrets / authentification | — | l'agent n'agit jamais, il escalade |

Par défaut `DRY_RUN=true` : aucune action réelle n'est exécutée (simulation).

## Installation

Prérequis : Python 3.11 à 3.13 et Node 18+ (pour l'interface). Avec Python 3.14, la version épinglée de `pydantic-core` nécessite une compilation native.

**Linux/macOS :**

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --reload
```

**Windows PowerShell :**

Install Python 3.13 first if `py -3.13` is not available (for example, run `winget install --id Python.Python.3.13 -e`), then open a new PowerShell window.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.main:app --reload
```

Interface React (dans un second terminal) :

```bash
cd frontend && npm install && npm run dev               # http://localhost:5173
```

## Exemple d'appel

```bash
curl -X POST localhost:8000/analyze -H "Content-Type: application/json" \
     -d '{"run_id": "run-missing-dep"}'
```

Réponse (extrait) : `category: missing_dependency`, `proposed_fix: Ajouter ... pandas ...`,
`status: resolved_auto`. Les runs d'exemple sont dans `data/logs/` (mode `mock`, aucun compte requis).

## API

| Route | Rôle |
| --- | --- |
| `GET /health` | santé et mode courant |
| `GET /runs` | runs disponibles (mock) |
| `POST /analyze` | analyser un run (`run_id`) ou un log collé (`log_text`) |
| `GET /incidents`, `GET /incidents/{id}` | incidents et diagnostics |
| `POST /incidents/{id}/approve` / `reject` | validation humaine |
| `GET /audit` | journal d'audit |

Erreurs au format stable : `{"error": {"code": "...", "message": "..."}}`.

## Tests, qualité, évaluation

```bash
pytest -q                          # tests
ruff check .                       # lint (lancé aussi par la CI)
python scripts/evaluate.py --write # mesure sur data/eval_cases.json -> docs/evaluation.md
```

## Structure

```
src/        main.py (API) · agent.py (boucle) · analyzer.py · policy.py · actions.py
            cicd.py (mock + GitHub) · llm.py (optionnel) · audit.py · schemas.py · config.py
tests/      tests de l'analyseur, de la politique et de l'API
data/       logs d'exemple et jeu d'évaluation
docs/       cahier des charges (LaTeX), architecture, évaluation, fiches de suivi
frontend/   interface React (Vite)
scripts/    evaluate.py
```

## Mode GitHub réel (optionnel)

Dans `.env` : `CICD_MODE=github`, `GITHUB_TOKEN`, `GITHUB_REPO`. Garder `DRY_RUN=true` tant que
les règles ne sont pas validées. Le token ne doit jamais être commité.

## Limites connues

- L'analyse repose sur des signatures d'erreurs : un log inédit entraîne une abstention (escalade humaine).
- `open_pr` côté GitHub reste à implémenter (prévu en semaine 3) ; en mock il est simulé.
- Les 19 cas d'évaluation fournis sont des exemples de départ : à remplacer/compléter par de vrais logs.
