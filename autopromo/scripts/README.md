Scripts de l’auto-promotion. Aucune clé n’est stockée ici.

- `verifier_config.py` — à lancer **avant toute mise en ligne** de `config.json` :
  `python3 autopromo/scripts/verifier_config.py`
  Contrôle, pour chaque langue, que chaque jeu proposé a cette langue dans
  `jeux.X.langues`, que la Boule et le Génie sont présents partout où ils
  existent, qu’une appli source n’a de liste que dans ses propres langues,
  et qu’aucun jeu ne se propose lui-même. Échoue (code 1) en cas d’erreur.
  Branché sur chaque push via `.github/workflows/autopromo-config.yml`.

- `fetch_autopromo_stats.py` — génère `../stats.json` depuis l’API GA4
  (gratuit, lecture seule). Consignes : [`../STATISTIQUES.md`](../STATISTIQUES.md).
