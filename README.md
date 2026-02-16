# Cemantix local (prototype)

Ce dépôt propose une version **locale** inspirée de Cemantix, avec :

- une page **client** pour jouer ;
- une page **admin** pour voir les statistiques ;
- un stockage SQLite local ;
- un champ `pseudo` pour préparer les futures stats par joueur.

> ⚠️ Les données officielles de Cemantix ne sont pas distribuées publiquement dans ce projet. Cette version utilise un dictionnaire local que vous pouvez remplacer.

## Lancer en local

```bash
python -m venv .venv
source .venv/bin/activate
python app.py
```

Application disponible sur `http://127.0.0.1:5000`.

## Configuration

Variables d'environnement optionnelles :

- `ADMIN_TOKEN` : token requis pour l'API admin (défaut: `changeme`)
- `DATABASE_PATH` : chemin du fichier sqlite (défaut: `cemantix_local.db`)
- `PORT` : port HTTP (défaut: `5000`)
- `WORDS_DIR` : dossier de mots (défaut: `data/cemantix`)
- `WORDS_FILE` : fichier de mots (défaut: `data/cemantix/words_fr.txt`)

## Endpoints

- `GET /` : page client
- `GET /admin` : page admin
- `POST /api/guess` : envoie une proposition
- `GET /api/admin/stats?token=...` : stats agrégées + séries pour graphes
- `POST /api/admin/target` : change le mot actif (admin)

## Évolutions prévues

- Comptes utilisateurs (auth)
- Classements par pseudo
