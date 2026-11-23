"""Exécution des actions (relance, rollback, PR). DRY_RUN = simulation seulement."""
from .cicd import CICDClient
from .schemas import Incident


def execute(incident: Incident, client: CICDClient, dry_run: bool) -> dict:
    action = incident.diagnosis.recommended_action
    if action == "none":
        return {"executed": False, "reason": "aucune action"}
    if dry_run:
        return {"executed": False, "simulated": True, "action": action,
                "note": "DRY_RUN actif : aucune action réelle."}
    run_id = incident.run_id or ""
    if action == "rerun_job":
        result = client.rerun(run_id)
    elif action == "rollback":
        result = client.rollback(run_id, incident.environment)
    else:
        result = client.open_pr(run_id, f"fix(ci): {incident.diagnosis.category}",
                                incident.diagnosis.proposed_fix)
    return {"executed": True, **result}
