"""Configuration lue depuis les variables d'environnement (.env)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    cicd_mode: str
    dry_run: bool
    auto_actions: bool
    confidence_threshold: float
    max_retries: int
    max_log_chars: int
    audit_db: str
    anthropic_api_key: str
    anthropic_model: str
    github_token: str
    github_repo: str
    github_rollback_workflow: str


def get_settings() -> Settings:
    """Relit l'environnement à chaque appel (pratique pour les tests)."""
    return Settings(
        cicd_mode=os.getenv("CICD_MODE", "mock"),
        dry_run=_bool("DRY_RUN", "true"),
        auto_actions=_bool("AUTO_ACTIONS", "true"),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.70")),
        max_retries=int(os.getenv("MAX_RETRIES", "2")),
        max_log_chars=int(os.getenv("MAX_LOG_CHARS", "20000")),
        audit_db=os.getenv("AUDIT_DB", "data/audit.db"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_repo=os.getenv("GITHUB_REPO", ""),
        github_rollback_workflow=os.getenv("GITHUB_ROLLBACK_WORKFLOW", "rollback.yml"),
    )
