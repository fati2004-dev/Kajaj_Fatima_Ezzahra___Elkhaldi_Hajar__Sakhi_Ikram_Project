"""Explication en langage naturel via un LLM (optionnel). Échec = mode dégradé, jamais bloquant."""
import httpx

from .config import Settings
from .schemas import Diagnosis

SYSTEM = (
    "Tu es un ingénieur DevOps. Explique en français, en 4 phrases max, la cause probable de "
    "l'échec CI/CD et la correction à appliquer. Ne propose jamais de commande destructive "
    "et ne demande ni ne répète aucun secret."
)


def explain(diagnosis: Diagnosis, log_tail: str, settings: Settings) -> str | None:
    if not settings.anthropic_api_key:
        return None
    prompt = (
        f"Diagnostic automatique : {diagnosis.category} (étape : {diagnosis.stage}).\n"
        f"Fin du log (secrets masqués) :\n{log_tail[-3000:]}"
    )
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"},
            json={"model": settings.anthropic_model, "max_tokens": 400, "system": SYSTEM,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json()["content"]).strip() or None
    except (httpx.HTTPError, KeyError, ValueError):
        return None  # service externe indisponible : on garde le diagnostic par règles
