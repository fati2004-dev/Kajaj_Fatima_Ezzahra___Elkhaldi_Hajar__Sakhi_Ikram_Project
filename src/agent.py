"""Boucle de l'agent : récupérer les logs -> analyser -> expliquer -> décider -> (agir)."""
import uuid

from . import actions, audit, llm, policy
from .analyzer import analyze, prepare_log
from .cicd import CICDClient, CICDError
from .config import Settings
from .schemas import AnalyzeRequest, Incident


class IncidentNotFound(Exception):
    pass


class InvalidState(Exception):
    pass


class Agent:
    def __init__(self, client: CICDClient, settings: Settings):
        self.client, self.settings = client, settings
        self.incidents: dict[str, Incident] = {}

    # -- outils de l'agent (chaque appel est tracé) ---------------------------------
    def handle(self, req: AnalyzeRequest) -> Incident:
        trace: list[dict] = []

        # Outil 1 : fetch_logs
        if req.log_text is not None:
            raw = req.log_text
            trace.append({"tool": "fetch_logs", "source": "request", "chars": len(raw)})
        else:
            raw = self.client.get_logs(req.run_id or "")  # peut lever CICDError
            trace.append({"tool": "fetch_logs", "source": req.run_id, "chars": len(raw)})

        # Outil 2 : analyze_logs
        diagnosis = analyze(raw, self.settings.max_log_chars)
        trace.append({"tool": "analyze_logs", "category": diagnosis.category,
                      "confidence": diagnosis.confidence, "abstained": diagnosis.abstained})

        # Outil 3 (optionnel) : explain_with_llm — jamais bloquant
        tail = prepare_log(raw, self.settings.max_log_chars)
        explanation = llm.explain(diagnosis, tail, self.settings)
        trace.append({"tool": "explain_with_llm", "used": explanation is not None})

        # Décision de sécurité
        decision = policy.decide(diagnosis.recommended_action, diagnosis.confidence, 0, self.settings)
        trace.append({"tool": "policy", "risk": decision.risk, "auto": decision.auto_allowed})

        incident = Incident(
            id=uuid.uuid4().hex[:8], run_id=req.run_id, environment=req.environment,
            diagnosis=diagnosis, decision=decision, status="no_action",
            llm_explanation=explanation, trace=trace,
        )
        audit.log_event(incident.id, "agent", "diagnosed",
                        {"category": diagnosis.category, "confidence": diagnosis.confidence})

        if decision.auto_allowed:
            incident.action_result = actions.execute(incident, self.client, self.settings.dry_run)
            incident.status = "resolved_auto"
            audit.log_event(incident.id, "agent", "action_auto", incident.action_result)
        elif decision.requires_approval:
            incident.status = "awaiting_approval"
            audit.log_event(incident.id, "agent", "approval_requested",
                            {"action": diagnosis.recommended_action, "reason": decision.reason})
        self.incidents[incident.id] = incident
        return incident

    # -- validation humaine -----------------------------------------------------------
    def _pending(self, incident_id: str) -> Incident:
        incident = self.incidents.get(incident_id)
        if incident is None:
            raise IncidentNotFound(incident_id)
        if incident.status != "awaiting_approval":
            raise InvalidState(f"statut actuel : {incident.status}")
        return incident

    def approve(self, incident_id: str, approver: str = "human") -> Incident:
        incident = self._pending(incident_id)
        try:
            incident.action_result = actions.execute(incident, self.client, self.settings.dry_run)
        except CICDError as exc:
            incident.action_result = {"executed": False, "error": exc.message}
        incident.status = "executed"
        audit.log_event(incident.id, approver, "approved_and_executed", incident.action_result)
        return incident

    def reject(self, incident_id: str, approver: str = "human") -> Incident:
        incident = self._pending(incident_id)
        incident.status = "rejected"
        audit.log_event(incident.id, approver, "rejected", {})
        return incident
