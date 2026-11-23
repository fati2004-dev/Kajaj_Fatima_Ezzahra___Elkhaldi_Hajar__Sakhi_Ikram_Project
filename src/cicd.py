"""Connecteurs CI/CD. MockClient (démo/tests, sans compte) et GitHubClient (GitHub Actions)."""
import io
import zipfile
from pathlib import Path
from typing import Protocol

import httpx

from .config import Settings

LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"


class CICDError(Exception):
    def __init__(self, code: str, message: str, status: int = 502):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class CICDClient(Protocol):
    def list_runs(self) -> list[str]: ...
    def get_logs(self, run_id: str) -> str: ...
    def rerun(self, run_id: str) -> dict: ...
    def rollback(self, run_id: str, environment: str) -> dict: ...
    def open_pr(self, run_id: str, title: str, body: str) -> dict: ...


class MockClient:
    def list_runs(self) -> list[str]:
        return sorted(p.stem for p in LOG_DIR.glob("*.log"))

    def get_logs(self, run_id: str) -> str:
        path = LOG_DIR / f"{Path(run_id).name}.log"  # Path().name bloque ../ (path traversal)
        if not path.exists():
            raise CICDError("run_not_found", f"run inconnu : {run_id}", 404)
        return path.read_text(encoding="utf-8")

    def rerun(self, run_id: str) -> dict:
        return {"mock": True, "action": "rerun_job", "run_id": run_id}

    def rollback(self, run_id: str, environment: str) -> dict:
        return {"mock": True, "action": "rollback", "run_id": run_id, "environment": environment}

    def open_pr(self, run_id: str, title: str, body: str) -> dict:
        return {"mock": True, "action": "open_pr", "title": title}


class GitHubClient:
    API = "https://api.github.com"

    def __init__(self, settings: Settings):
        if not settings.github_token or not settings.github_repo:
            raise CICDError("config_error", "GITHUB_TOKEN et GITHUB_REPO requis", 500)
        self.repo = settings.github_repo
        self.rollback_workflow = settings.github_rollback_workflow
        self.http = httpx.Client(
            base_url=self.API, timeout=20, follow_redirects=True,
            headers={"Authorization": f"Bearer {settings.github_token}",
                     "Accept": "application/vnd.github+json"},
        )

    def _call(self, method: str, url: str, **kw) -> httpx.Response:
        try:
            resp = self.http.request(method, url, **kw)
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as exc:
            raise CICDError("cicd_unavailable", f"GitHub indisponible : {exc}") from exc

    def list_runs(self) -> list[str]:
        data = self._call("GET", f"/repos/{self.repo}/actions/runs",
                          params={"status": "failure", "per_page": 10}).json()
        return [str(r["id"]) for r in data.get("workflow_runs", [])]

    def get_logs(self, run_id: str) -> str:
        content = self._call("GET", f"/repos/{self.repo}/actions/runs/{run_id}/logs").content
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return "\n".join(zf.read(n).decode("utf-8", "replace") for n in zf.namelist())

    def rerun(self, run_id: str) -> dict:
        self._call("POST", f"/repos/{self.repo}/actions/runs/{run_id}/rerun-failed-jobs")
        return {"action": "rerun_job", "run_id": run_id}

    def rollback(self, run_id: str, environment: str) -> dict:
        # Convention : un workflow « rollback.yml » (workflow_dispatch) redéploie la version saine.
        self._call("POST", f"/repos/{self.repo}/actions/workflows/{self.rollback_workflow}/dispatches",
                   json={"ref": "main", "inputs": {"environment": environment}})
        return {"action": "rollback", "environment": environment}

    def open_pr(self, run_id: str, title: str, body: str) -> dict:
        raise CICDError("not_implemented", "open_pr GitHub : à implémenter en S3", 501)


def get_client(settings: Settings) -> CICDClient:
    return GitHubClient(settings) if settings.cicd_mode == "github" else MockClient()
