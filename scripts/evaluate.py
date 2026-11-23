"""Évalue l'analyseur sur data/eval_cases.json.
Usage : python scripts/evaluate.py [--write]   (--write met à jour docs/evaluation.md)
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analyzer import analyze  # noqa: E402

CRITERES = {"exactitude_categorie": 0.85, "exactitude_action": 0.85}


def main() -> int:
    cases = json.loads((ROOT / "data" / "eval_cases.json").read_text(encoding="utf-8"))
    ok_cat = ok_act = 0
    erreurs = []
    for c in cases:
        d = analyze(c["log"])
        ok_cat += d.category == c["expected_category"]
        ok_act += d.recommended_action == c["expected_action"]
        if d.category != c["expected_category"]:
            erreurs.append(f"- {c['id']} : attendu `{c['expected_category']}`, obtenu `{d.category}`")
    n = len(cases)
    res = {"exactitude_categorie": ok_cat / n, "exactitude_action": ok_act / n}
    lignes = ["# Évaluation de l'Agent DevOps\n", f"Mesure du {date.today()} sur {n} cas.\n",
              "| Critère | Mesuré | Seuil | Verdict |", "| --- | --- | --- | --- |"]
    passed = True
    for k, seuil in CRITERES.items():
        v = res[k]
        passed &= v >= seuil
        lignes.append(f"| {k} | {v:.0%} | {seuil:.0%} | {'OK' if v >= seuil else 'KO'} |")
    lignes.append("\n## Erreurs\n" + ("\n".join(erreurs) if erreurs else "Aucune."))
    lignes.append("\n## Limites connues\n- Détection par signatures : un log inédit donne une abstention.\n"
                  "- Jeu d'évaluation petit (à élargir avec de vrais logs du groupe).")
    report = "\n".join(lignes)
    print(report)
    if "--write" in sys.argv:
        (ROOT / "docs" / "evaluation.md").write_text(report + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
