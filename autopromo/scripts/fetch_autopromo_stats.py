#!/usr/bin/env python3
"""Génère autopromo/stats.json à partir de l'API Google Analytics Data (GA4).

Gratuit : l'API n'a pas de facturation à l'appel, seulement un quota quotidien
(voir https://developers.google.com/analytics/devguides/reporting/data/v1/quotas).
Aucune clé n'est écrite dans le dépôt : le compte de service se lit via
GOOGLE_APPLICATION_CREDENTIALS (fichier local ou secret GitHub Actions).

Variables d'environnement :
  GA4_PROPERTY_ID                 identifiant numérique de la propriété GA4
  GOOGLE_APPLICATION_CREDENTIALS  chemin vers la clé JSON du compte de service
  GA4_START_DATE                  défaut : 2020-01-01
  GA4_END_DATE                    défaut : today

Usage :
  python3 fetch_autopromo_stats.py --output ../stats.json
  python3 fetch_autopromo_stats.py --self-test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
SCOPES = ("https://www.googleapis.com/auth/analytics.readonly",)
API = "https://analyticsdata.googleapis.com/v1beta"
EVENT_VIEW = "cross_promo_view"
EVENT_CLICK = "cross_promo_click"
CUSTOM_DIMS = ("jeu_source", "jeu_cible", "langue", "emplacement")
PAGE_SIZE = 10000

# Zora (et d'anciennes versions) envoient parfois le paquet Play au lieu de l'id court.
ID_COURTS = {
    "boule": "boule",
    "genie": "genie",
    "zora": "zora",
    "oracle": "oracle",
    "coeur": "coeur",
    "monoracle": "monoracle",
    "com.kuriocie.boule_voyance": "boule",
    "com.kuriocie.lampe_genie": "genie",
    "com.zora.voyancegitane": "zora",
    "com.zora.voyancegitane.test": "zora",
    "com.kuriocie.oracle_animaux": "oracle",
    "com.kuriocie.coeurdescouleurs": "coeur",
    "com.kuriocie.monoracle": "monoracle",
}


def id_court(valeur: str) -> str:
    v = (valeur or "").strip()
    if not v or v in ("(not set)", "(other)"):
        return v
    return ID_COURTS.get(v, v)


def _vide(valeur: str) -> bool:
    return (not valeur) or valeur in ("(not set)", "(other)")


def fusionner(vues: dict[tuple, int], clics: dict[tuple, int]) -> list[dict[str, Any]]:
    cles = set(vues) | set(clics)
    lignes = []
    for cle in cles:
        src, cible, langue, empl = cle
        lignes.append(
            {
                "jeu_source": src,
                "jeu_cible": cible,
                "langue": langue,
                "emplacement": empl,
                "vues": int(vues.get(cle, 0)),
                "clics": int(clics.get(cle, 0)),
            }
        )
    lignes.sort(key=lambda r: (-r["vues"], -r["clics"], r["jeu_source"], r["jeu_cible"], r["langue"], r["emplacement"]))
    return lignes


def lignes_depuis_rapport(rows: list[dict], extraire_dims: bool) -> dict[tuple, int]:
    out: dict[tuple, int] = {}
    for row in rows:
        dims = [d.get("value", "") for d in row.get("dimensionValues", [])]
        metrics = [m.get("value", "0") for m in row.get("metricValues", [])]
        n = int(metrics[0] or 0) if metrics else 0
        if extraire_dims:
            # eventName, jeu_source, jeu_cible, langue, emplacement
            src = id_court(dims[1] if len(dims) > 1 else "")
            cible = id_court(dims[2] if len(dims) > 2 else "")
            langue = dims[3] if len(dims) > 3 else ""
            empl = dims[4] if len(dims) > 4 else ""
            if _vide(empl):
                empl = ""
            if _vide(src):
                src = "(non renseigné)"
            if _vide(cible):
                cible = "(non renseigné)"
            if _vide(langue):
                langue = "(non renseigné)"
        else:
            src = "(tous)"
            cible = "(tous)"
            langue = "(toutes)"
            empl = "non ventilé (dimensions GA4 pas encore actives)"
        cle = (src, cible, langue, empl)
        out[cle] = out.get(cle, 0) + n
    return out


def construire_stats(
    *,
    periode: str,
    vues: dict[tuple, int],
    clics: dict[tuple, int],
    ventile: bool,
    avertissement: str | None = None,
) -> dict[str, Any]:
    maintenant = datetime.now(PARIS)
    data: dict[str, Any] = {
        "periode": periode,
        "source": "API Google Analytics Data (GA4), projet Firebase kuriocie-jeux",
        "evenements": [EVENT_VIEW, EVENT_CLICK],
        "genere_le": maintenant.strftime("%Y-%m-%d %H:%M %Z"),
        "ventile": ventile,
        "lignes": fusionner(vues, clics),
    }
    if avertissement:
        data["avertissement"] = avertissement
    return data


def credentials():
    try:
        from google.auth import default as google_auth_default
        from google.oauth2 import service_account
    except ImportError as exc:
        raise SystemExit(
            "Le module google-auth manque. Installez-le avec : pip install 'google-auth>=2'"
        ) from exc

    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path:
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    creds, _ = google_auth_default(scopes=SCOPES)
    return creds


def access_token(creds) -> str:
    from google.auth.transport.requests import Request

    if not creds.valid:
        creds.refresh(Request())
    return creds.token


def run_report(token: str, property_id: str, body: dict) -> dict:
    url = f"{API}/properties/{property_id}:runReport"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API GA4 HTTP {exc.code} : {detail[:2000]}") from exc


def toutes_les_lignes(token: str, property_id: str, body: dict) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = dict(body)
        page["limit"] = PAGE_SIZE
        page["offset"] = offset
        payload = run_report(token, property_id, page)
        batch = payload.get("rows") or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def corps_rapport(start: str, end: str, events: list[str], avec_dimensions: bool) -> dict:
    dimensions = [{"name": "eventName"}]
    if avec_dimensions:
        dimensions.extend({"name": f"customEvent:{n}"} for n in CUSTOM_DIMS)
    filtres = [{"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "EXACT", "value": ev}}} for ev in events]
    dimension_filter: dict[str, Any]
    if len(filtres) == 1:
        dimension_filter = filtres[0]
    else:
        dimension_filter = {"orGroup": {"expressions": filtres}}
    return {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": dimensions,
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": dimension_filter,
        "keepEmptyRows": False,
    }


def est_erreur_dimensions(message: str) -> bool:
    bas = message.lower()
    indices = (
        "customevent:",
        "custom dimension",
        "dimension is not recognized",
        "field is not recognized",
        "is not a valid dimension",
        "invalid argument",
        "not found",
    )
    return any(s in bas for s in indices)


def separer_par_evenement(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    vues, clics = [], []
    for row in rows:
        nom = (row.get("dimensionValues") or [{}])[0].get("value", "")
        if nom == EVENT_VIEW:
            vues.append(row)
        elif nom == EVENT_CLICK:
            clics.append(row)
    return vues, clics


def recuperer(token: str, property_id: str, start: str, end: str) -> dict[str, Any]:
    periode = f"{start} → {end}"
    try:
        rows = toutes_les_lignes(token, property_id, corps_rapport(start, end, [EVENT_VIEW, EVENT_CLICK], True))
        vues_rows, clics_rows = separer_par_evenement(rows)
        return construire_stats(
            periode=periode,
            vues=lignes_depuis_rapport(vues_rows, True),
            clics=lignes_depuis_rapport(clics_rows, True),
            ventile=True,
        )
    except RuntimeError as exc:
        if not est_erreur_dimensions(str(exc)):
            raise
        rows = toutes_les_lignes(token, property_id, corps_rapport(start, end, [EVENT_VIEW, EVENT_CLICK], False))
        vues_rows, clics_rows = separer_par_evenement(rows)
        avert = (
            "Les totaux sont disponibles, mais le détail par jeu / langue / emplacement "
            "n'est pas encore lisible : les dimensions personnalisées jeu_source, "
            "jeu_cible, langue et emplacement doivent être créées dans GA4 "
            "(voir autopromo/STATISTIQUES.md). Compter 24 à 48 h après leur création."
        )
        return construire_stats(
            periode=periode,
            vues=lignes_depuis_rapport(vues_rows, False),
            clics=lignes_depuis_rapport(clics_rows, False),
            ventile=False,
            avertissement=avert,
        )


def self_test() -> None:
    vues = lignes_depuis_rapport(
        [
            {
                "dimensionValues": [
                    {"value": EVENT_VIEW},
                    {"value": "boule"},
                    {"value": "com.kuriocie.lampe_genie"},
                    {"value": "pt-BR"},
                    {"value": "plus_de_jeux"},
                ],
                "metricValues": [{"value": "10"}],
            },
            {
                "dimensionValues": [
                    {"value": EVENT_VIEW},
                    {"value": "boule"},
                    {"value": "zora"},
                    {"value": "fr"},
                    {"value": "(not set)"},
                ],
                "metricValues": [{"value": "3"}],
            },
        ],
        True,
    )
    clics = lignes_depuis_rapport(
        [
            {
                "dimensionValues": [
                    {"value": EVENT_CLICK},
                    {"value": "boule"},
                    {"value": "genie"},
                    {"value": "pt-BR"},
                    {"value": "plus_de_jeux"},
                ],
                "metricValues": [{"value": "2"}],
            }
        ],
        True,
    )
    data = construire_stats(periode="test", vues=vues, clics=clics, ventile=True)
    assert data["lignes"][0]["jeu_cible"] == "genie"
    assert data["lignes"][0]["vues"] == 10
    assert data["lignes"][0]["clics"] == 2
    assert data["lignes"][1]["emplacement"] == ""
    assert data["lignes"][1]["vues"] == 3
    assert data["evenements"] == [EVENT_VIEW, EVENT_CLICK]
    # schéma compatible avec stats.exemple.json
    for ligne in data["lignes"]:
        for champ in ("jeu_source", "jeu_cible", "langue", "emplacement", "vues", "clics"):
            assert champ in ligne
    print("self-test ok")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Génère stats.json depuis l'API GA4 (gratuit, lecture seule).")
    parser.add_argument("--output", "-o", help="Chemin du fichier stats.json à écrire")
    parser.add_argument("--self-test", action="store_true", help="Vérifie le format sans appeler l'API")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0

    property_id = (os.environ.get("GA4_PROPERTY_ID") or "").strip()
    if not property_id:
        print(
            "Il manque GA4_PROPERTY_ID (numéro de la propriété GA4 liée à kuriocie-jeux). "
            "Voir autopromo/STATISTIQUES.md.",
            file=sys.stderr,
        )
        return 2
    if property_id.startswith("properties/"):
        property_id = property_id.split("/", 1)[1]

    start = (os.environ.get("GA4_START_DATE") or "2020-01-01").strip()
    end = (os.environ.get("GA4_END_DATE") or "today").strip()
    if end == "today":
        end = date.today().isoformat()

    creds = credentials()
    token = access_token(creds)
    data = recuperer(token, property_id, start, end)

    texte = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(texte, encoding="utf-8")
        print(f"Écrit {dest} ({len(data['lignes'])} ligne(s), ventile={data['ventile']})", file=sys.stderr)
    else:
        sys.stdout.write(texte)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
