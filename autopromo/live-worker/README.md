Worker Cloudflare `autopromo-live` (https://autopromo-live.kuriocie23.workers.dev).

Déploiement (compte kuriocie23, wrangler déjà connecté) :

```bash
cd autopromo/live-worker
wrangler deploy
wrangler secret put GA4_SERVICE_ACCOUNT_JSON < /workspace/secrets/autopromo_stats_sa.json
```

La clé n’est ni dans ce dossier ni dans le Drive. Voir `../STATISTIQUES.md`.
