#!/usr/bin/env python3
"""Contrôle la config d'auto-promotion avant mise en ligne.

Échoue (code 1) si une règle est violée :
- un jeu proposé dans une langue où son interface n'existe pas ;
- une appli source qui a une liste pour une langue qu'elle n'a pas ;
- un jeu qui se propose lui-même ;
- la Boule ou le Génie absents d'une langue où ils existent (sauf s'ils sont la source).

Usage :
  python3 autopromo/scripts/verifier_config.py
  python3 autopromo/scripts/verifier_config.py chemin/vers/config.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


JEUX_OBLIGATOIRES = ("boule", "genie")


def item_id(it):
    if isinstance(it, dict):
        return it.get("id")
    return it


def verifier(config: dict) -> list[str]:
    erreurs: list[str] = []
    jeux = config.get("jeux") or {}
    sources = config.get("sources") or {}

    if not jeux or not sources:
        return ["Config invalide : clés jeux ou sources manquantes."]

    for src, val in sources.items():
        if src not in jeux:
            erreurs.append(f"Source « {src} » absente de jeux.")
            continue
        src_langs = list((jeux[src] or {}).get("langues") or [])
        par = (val or {}).get("par_langue") or {}

        extra = sorted(set(par) - set(src_langs))
        if extra:
            erreurs.append(
                f"Source « {src} » : listes par_langue pour {len(extra)} langue(s) "
                f"où cette appli n'est pas traduite ({', '.join(extra[:12])}"
                f"{'…' if len(extra) > 12 else ''}). "
                f"Une source n'a de liste que dans ses propres langues "
                f"(jeux.{src}.langues)."
            )

        manquantes = sorted(set(src_langs) - set(par))
        if manquantes:
            erreurs.append(
                f"Source « {src} » : langues de l'appli sans entrée par_langue : "
                f"{', '.join(manquantes[:12])}{'…' if len(manquantes) > 12 else ''}."
            )

        for lang, items in par.items():
            ids = []
            for it in items or []:
                iid = item_id(it)
                if not iid:
                    erreurs.append(f"Source « {src} » / {lang} : entrée sans id.")
                    continue
                ids.append(iid)
                if iid == src:
                    erreurs.append(
                        f"Source « {src} » / {lang} : le jeu se propose lui-même."
                    )
                cible = jeux.get(iid)
                if not cible:
                    erreurs.append(
                        f"Source « {src} » / {lang} : jeu inconnu « {iid} »."
                    )
                    continue
                if lang not in (cible.get("langues") or []):
                    erreurs.append(
                        f"Source « {src} » / {lang} : « {iid} » est proposé alors que "
                        f"son interface n'existe pas dans cette langue "
                        f"(jeux.{iid}.langues = {cible.get('langues')})."
                    )

            if lang in src_langs:
                for must in JEUX_OBLIGATOIRES:
                    if must == src:
                        continue
                    cible = jeux.get(must) or {}
                    if not cible.get("published"):
                        continue
                    if lang in (cible.get("langues") or []) and must not in ids:
                        erreurs.append(
                            f"Source « {src} » / {lang} : « {must} » manque, alors "
                            f"qu'il est traduit dans cette langue."
                        )
    return erreurs


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        path = Path(argv[1])
    else:
        path = Path(__file__).resolve().parent.parent / "config.json"

    if not path.is_file():
        print(f"ERREUR : fichier introuvable : {path}", file=sys.stderr)
        return 1

    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERREUR : JSON invalide dans {path} : {exc}", file=sys.stderr)
        return 1

    erreurs = verifier(config)
    if erreurs:
        print(f"ÉCHEC : {len(erreurs)} erreur(s) dans {path}", file=sys.stderr)
        for e in erreurs:
            print(f"  - {e}", file=sys.stderr)
        return 1

    n_src = len(config.get("sources") or {})
    n_jeux = len(config.get("jeux") or {})
    print(f"OK : {path} ({n_src} sources, {n_jeux} jeux, règles respectées).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
