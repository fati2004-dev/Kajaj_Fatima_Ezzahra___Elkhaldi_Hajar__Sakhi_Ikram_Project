"""API FastAPI de l'Agent DevOps. Lancer : uvicorn src.main:app --reload"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import audit
from .agent import Agent, IncidentNotFound, InvalidState
from .cicd import CICDError, get_client
from .config import get_settings
from .schemas import AnalyzeRequest, Incident


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


def create_app() -> FastAPI:
    settings = get_settings()
    agent = Agent(get_client(settings), settings)
    app = FastAPI(title="Agent DevOps", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(map(str, e["loc"][1:])), "message": e["msg"]}
                   for e in exc.errors()]
        return _error(422, "validation_error", "Entrée invalide", details)

    @app.exception_handler(CICDError)
    async def _cicd(_: Request, exc: CICDError):
        return _error(exc.status, exc.code, exc.message)

    @app.exception_handler(IncidentNotFound)
    async def _not_found(_: Request, exc: IncidentNotFound):
        return _error(404, "incident_not_found", f"incident inconnu : {exc}")

    @app.exception_handler(InvalidState)
    async def _state(_: Request, exc: InvalidState):
        return _error(409, "invalid_state", f"action impossible ({exc})")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": settings.cicd_mode, "dry_run": settings.dry_run}

    @app.get("/runs")
    def runs() -> list[str]:
        return agent.client.list_runs()

    @app.post("/analyze", response_model=Incident)
    def analyze_run(req: AnalyzeRequest):
        return agent.handle(req)

    @app.get("/incidents", response_model=list[Incident])
    def incidents():
        return sorted(agent.incidents.values(), key=lambda i: i.created_at, reverse=True)

    @app.get("/incidents/{incident_id}", response_model=Incident)
    def incident(incident_id: str):
        if incident_id not in agent.incidents:
            raise IncidentNotFound(incident_id)
        return agent.incidents[incident_id]

    @app.post("/incidents/{incident_id}/approve", response_model=Incident)
    def approve(incident_id: str):
        return agent.approve(incident_id)

    @app.post("/incidents/{incident_id}/reject", response_model=Incident)
    def reject(incident_id: str):
        return agent.reject(incident_id)

    @app.get("/audit")
    def audit_log(limit: int = 100):
        return audit.list_events(min(limit, 500))

    return app


app = create_app()
