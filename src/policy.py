"""Règles de sécurité : qui a le droit de faire quoi, avec ou sans validation humaine."""
from .config import Settings
from .schemas import Decision

RISK = {"none": "none", "rerun_job": "low", "open_pr": "medium", "rollback": "high"}


def decide(action: str, confidence: float, retries: int, settings: Settings) -> Decision:
    risk = RISK[action]
    if action == "none":
        return Decision(risk="none", auto_allowed=False, requires_approval=False,
                        reason="Aucune action recommandée.")
    if action == "rollback":
        return Decision(risk=risk, auto_allowed=False, requires_approval=True,
                        reason="Rollback : action sensible, validation humaine obligatoire.")
    if confidence < settings.confidence_threshold:
        return Decision(risk=risk, auto_allowed=False, requires_approval=True,
                        reason="Confiance sous le seuil : validation humaine requise.")
    if action == "rerun_job" and retries >= settings.max_retries:
        return Decision(risk=risk, auto_allowed=False, requires_approval=True,
                        reason="Nombre maximal de relances automatiques atteint.")
    if not settings.auto_actions:
        return Decision(risk=risk, auto_allowed=False, requires_approval=True,
                        reason="Actions automatiques désactivées (AUTO_ACTIONS=false).")
    return Decision(risk=risk, auto_allowed=True, requires_approval=False,
                    reason="Action à risque maîtrisé, autorisée automatiquement.")
