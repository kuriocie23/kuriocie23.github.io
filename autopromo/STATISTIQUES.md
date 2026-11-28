# Statistiques auto-promotion (clics) — marche à suivre

Document du 28 novembre 2026 (Europe/Paris). Aucun mot de passe ni clé ici.

La page https://kuriocie23.github.io/autopromo/ (onglet « Affichages et clics ») lit le fichier `stats.json` déposé à côté d’elle. Ce fichier n’existait pas encore : le tableau restait vide.

## Solution choisie (gratuite, la plus simple)

**API Google Analytics Data (GA4)**, avec un compte de service **en lecture seule**.

Pourquoi pas l’export BigQuery : c’est plus lourd, le bac à sable gratuit a une limite de stockage (10 Gio à vie) et des tables qui peuvent expirer, et une fausse manœuvre peut activer la facturation. L’API Data n’a pas de prix à l’appel, seulement un quota quotidien gratuit. Références officielles :

- Démarrage et compte de service en lecture (rôle Viewer suffisant) : https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries
- Quotas (pas de tarif, seulement des plafonds) : https://developers.google.com/analytics/devguides/reporting/data/v1/quotas
- Noms d’API des dimensions d’événement : `customEvent:jeu_source`, etc. : https://developers.google.com/analytics/devguides/reporting/data/v1/advanced
- Créer les dimensions dans GA4 : https://support.google.com/analytics/answer/14239696?hl=fr

Ne **jamais** activer la facturation Google Cloud, ni l’export BigQuery, pour cette tâche. Si une page demande une carte bancaire ou « Activer la facturation », annuler et s’arrêter.

Projet Firebase / Google Cloud : `kuriocie-jeux` (n° `666068648609`), compte Google `kuriocie23`. Événements `cross_promo_view` et `cross_promo_click`, paramètres `jeu_source`, `jeu_cible`, `langue`, `emplacement`. Envoyés par la Boule, Zora et l’Oracle ; le Génie bientôt.

Les paramètres ne sont lisibles dans l’API **qu’après** avoir été déclarés comme dimensions personnalisées de portée Événement. Compter 24 à 48 h. Le détail par jeu / langue ne remonte en général **pas** pour les événements antérieurs à cette déclaration. En attendant, le script écrit quand même les totaux (ligne « non ventilé »).

## Déjà en place dans ce dépôt (28/11/2026)

- Script : `autopromo/scripts/fetch_autopromo_stats.py`
- Automatisation quotidienne (07:00 Europe/Paris en hiver) : `.github/workflows/autopromo-stats.yml`
- La page charge automatiquement `stats.json` dès qu’il est publié. On peut aussi l’importer à la main (modèle : `stats.exemple.json`).

Les réglages des consoles et le secret GitHub ont été posés le 28 novembre 2026 (voir la section « État au 28 novembre 2026 » plus bas). Le détail par jeu et par langue peut rester vide 24 à 48 h.

## Marche à suivre des consoles (fait le 28/11/2026, conservé comme mode d’emploi)

Ces clics ont déjà été faits. Ils restent ici au cas où il faudrait recommencer (nouvelle clé, nouvelle propriété). Faire tout avec le compte **kuriocie23**. Ne jamais coller la clé JSON dans le dépôt, un document Drive, un chat ou un e-mail.

### 1. Noter le numéro de la propriété GA4

1. Ouvrir https://console.firebase.google.com/project/kuriocie-jeux/settings/integrations
2. Carte **Google Analytics** : ouvrir la propriété liée (elle s’appelle en général comme le projet).
3. Dans Google Analytics : icône rouage **Administration** (bas à gauche) → **Paramètres de la propriété** (ou « Property details »).
4. Copier le **Numéro de propriété** (chiffres seulement, par ex. `123456789`). C’est le `GA4_PROPERTY_ID`.

On peut aussi passer par https://analytics.google.com/analytics/web/ puis le sélecteur de propriété, en choisissant celle liée à `kuriocie-jeux`.

### 2. Activer l’API (sans facturation)

1. Ouvrir https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com?project=kuriocie-jeux
2. Vérifier que le projet en haut est bien **kuriocie-jeux**.
3. Cliquer sur **Activer**. Si le bouton dit déjà « Gérer », c’est bon.
4. Si Google propose d’**activer la facturation** ou de saisir une carte : **Annuler**. L’API Data fonctionne sans ça.

### 3. Créer un compte de service en lecture seule

1. Ouvrir https://console.cloud.google.com/iam-admin/serviceaccounts?project=kuriocie-jeux
2. **Créer un compte de service**.
3. Nom : `autopromo-stats`. L’adresse sera du type `autopromo-stats@kuriocie-jeux.iam.gserviceaccount.com`. La noter.
4. **Créer et continuer**. À « Accorder l’accès de ce compte de service au projet », **ne rien donner** (passer). Le droit de lecture se donne dans GA4, pas dans Cloud.
5. **OK** / **OK** / **Terminé**.
6. Cliquer sur le compte créé → onglet **Clés** → **Ajouter une clé** → **Créer une clé** → type **JSON** → **Créer**. Le fichier se télécharge **une seule fois**. Le garder dans un gestionnaire de mots de passe ou une clé USB, pas sur Drive.

Doc officielle : https://cloud.google.com/iam/docs/service-accounts-create

### 4. Donner au compte le rôle Lecteur sur la propriété GA4

1. Dans Google Analytics, propriété de `kuriocie-jeux` : **Administration** → **Gestion des accès à la propriété**.
2. **+** → **Ajouter des utilisateurs**.
3. Coller l’adresse `autopromo-stats@kuriocie-jeux.iam.gserviceaccount.com`.
4. Rôle : **Lecteur** (Viewer). Décocher « Informer les nouveaux utilisateurs par e-mail » (cette adresse n’a pas de boîte).
5. **Ajouter**.

Aide : https://support.google.com/analytics/answer/9305886?hl=fr

### 5. Déclarer les 4 dimensions personnalisées

Aide officielle : https://support.google.com/analytics/answer/14239696?hl=fr

1. Toujours dans cette propriété : **Administration** → **Affichage des données** → **Définitions personnalisées**.
2. Onglet **Dimensions personnalisées** → **Créer des dimensions personnalisées**.
3. Créer **quatre** dimensions, une par une, toutes en portée **Événement** :

| Nom de la dimension | Portée | Paramètre d’événement (exactement) |
|---|---|---|
| jeu_source | Événement | jeu_source |
| jeu_cible | Événement | jeu_cible |
| langue | Événement | langue |
| emplacement | Événement | emplacement |

4. **Enregistrer** à chaque fois. Si une dimension existe déjà avec le même paramètre, ne pas en créer une deuxième.
5. Attendre **24 à 48 h** avant que le détail apparaisse dans l’API.

### 6. Déposer le secret et le numéro dans GitHub (ce dépôt)

Dépôt : `kuriocie23/kuriocie23.github.io`.

1. Variable (pas un secret, juste le numéro) : https://github.com/kuriocie23/kuriocie23.github.io/settings/variables/actions
   - **New repository variable**
   - Nom : `GA4_PROPERTY_ID`
   - Valeur : le numéro copié à l’étape 1
2. Secret : https://github.com/kuriocie23/kuriocie23.github.io/settings/secrets/actions
   - **New repository secret**
   - Nom : `GA4_SERVICE_ACCOUNT_JSON`
   - Valeur : **tout** le contenu du fichier JSON téléchargé (de `{` à `}`). Rien d’autre dans ce champ.
3. Lancer une première fois à la main : https://github.com/kuriocie23/kuriocie23.github.io/actions/workflows/autopromo-stats.yml
   - **Run workflow** → branche `main` → **Run workflow**.
4. Si c’est vert, la page https://kuriocie23.github.io/autopromo/ (onglet Affichages et clics) affichera les totaux, puis le détail 24 à 48 h après l’étape 5. Ensuite le robot tourne tout seul chaque matin.

## Relancer le script à la main (robot remplaçant)

Une fois le secret et le numéro en place, le plus simple est de relancer le workflow (lien ci-dessus).

En local, **sans jamais committer la clé** :

```bash
export GA4_PROPERTY_ID="…numéro…"
export GOOGLE_APPLICATION_CREDENTIALS="/chemin/local/vers/la-cle.json"
python3 -m pip install "google-auth>=2"
python3 autopromo/scripts/fetch_autopromo_stats.py --output autopromo/stats.json
# Vérifier le fichier, puis le committer *seul* (pas la clé) et pousser.
```

Test du format, sans appeler l’API :

```bash
python3 autopromo/scripts/fetch_autopromo_stats.py --self-test
```

## Ce qu’il ne faut pas faire

- Activer la facturation Google Cloud, « Blaze », ou l’export BigQuery pour cette page.
- Mettre la clé JSON dans le dépôt, un gist, le Drive, ou PASSATION_CHEF.
- Utiliser un rôle plus élevé que Lecteur sur la propriété GA4.
- Modifier `main` d’un autre dépôt pour cette tâche.

## État au 28 novembre 2026 (branché, avec temps réel)

Tout ce qui suit a été fait, sans activer la facturation, sans mettre la clé dans le Drive ni dans le dépôt.

- Propriété GA4 : `563415076` (kuriocie-jeux).
- API Google Analytics Data activée sur le projet `kuriocie-jeux`.
- Dimensions personnalisées créées (portée Événement) : `jeu_source`, `jeu_cible`, `langue`, `emplacement`. Le détail par jeu et par langue n’apparaît en général que 24 à 48 h après, et pas pour les événements déjà passés. En attendant, le tableau quotidien affiche les totaux.
- Compte de service : `autopromo-stats@kuriocie-jeux.iam.gserviceaccount.com`, rôle Lecteur sur la propriété.
- Clé JSON : uniquement sur la box, fichier `/workspace/secrets/autopromo_stats_sa.json`. Ne jamais l’afficher, ni la copier dans le Drive, le dépôt ou un chat, ni la supprimer.
- Variable GitHub `GA4_PROPERTY_ID` et secret `GA4_SERVICE_ACCOUNT_JSON` posés sur le dépôt `kuriocie23/kuriocie23.github.io`.
- Workflow quotidien : https://github.com/kuriocie23/kuriocie23.github.io/actions/workflows/autopromo-stats.yml (chaque matin vers 7 h, heure de Paris en hiver, sans IA).
- Temps réel : Worker Cloudflare `autopromo-live`, adresse https://autopromo-live.kuriocie23.workers.dev/ — code dans `autopromo/live-worker/`. Il appelle `runRealtimeReport` (30 dernières minutes, totaux `cross_promo_view` / `cross_promo_click`), met le résultat en cache 60 s, et n’autorise le CORS que depuis `https://kuriocie23.github.io`. L’API Realtime n’accepte pas les dimensions d’événement : pas de détail par jeu en direct (doc : https://developers.google.com/analytics/devguides/reporting/data/v1/realtime-api-schema). La page n’a aucune clé : elle interroge seulement cette adresse, toutes les 60 s.
- Secret du Worker : `GA4_SERVICE_ACCOUNT_JSON` (la même clé, posée avec `wrangler secret put`, pas dans `wrangler.toml`).

### Relancer

- Totaux du matin : https://github.com/kuriocie23/kuriocie23.github.io/actions/workflows/autopromo-stats.yml — **Run workflow** — branche `main`. Ou, en local, sans committer la clé :

```bash
export GA4_PROPERTY_ID="563415076"
export GOOGLE_APPLICATION_CREDENTIALS="/workspace/secrets/autopromo_stats_sa.json"
python3 -m pip install "google-auth>=2" "requests>=2"
python3 autopromo/scripts/fetch_autopromo_stats.py --output autopromo/stats.json
# pousser seulement stats.json
```

- Temps réel (si le cadre « En direct » est vide) :

```bash
cd autopromo/live-worker
# wrangler est sur la box : /tmp/wr/node_modules/.bin/wrangler
wrangler deploy
# seulement si le secret a été perdu (ne pas afficher la clé) :
wrangler secret put GA4_SERVICE_ACCOUNT_JSON < /workspace/secrets/autopromo_stats_sa.json
curl -sS https://autopromo-live.kuriocie23.workers.dev/
```

