"""Analyse des logs CI/CD : règles (rapides, déterministes) + abstention si doute."""
import re
from dataclasses import dataclass

from .schemas import Diagnosis

SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key)\s*[=:]\s*\S+"),
]


def redact(text: str) -> str:
    """Masque les secrets avant stockage, affichage ou envoi à un LLM."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda m: m.group(0)[:4] + "***REDACTED***", text)
    return text


def prepare_log(raw: str, max_chars: int) -> str:
    """Nettoie, masque les secrets et garde la FIN du log (là où se trouve l'erreur)."""
    if not raw or not raw.strip():
        raise ValueError("le log est vide")
    text = redact(raw.replace("\r\n", "\n"))
    return text[-max_chars:] if len(text) > max_chars else text


@dataclass(frozen=True)
class Rule:
    category: str
    pattern: re.Pattern
    stage: str
    confidence: float
    action: str
    explanation: str
    fix: str


def _r(category, regex, stage, confidence, action, explanation, fix) -> Rule:
    return Rule(category, re.compile(regex, re.I), stage, confidence, action, explanation, fix)


# L'ordre = la priorité (la première règle qui matche gagne).
RULES: list[Rule] = [
    _r("auth_error", r"401 unauthorized|403 forbidden|permission denied \(publickey\)|"
       r"authentication failed|denied: requested access|bad credentials",
       "authentification", 0.90, "none",
       "Échec d'authentification ou de droits (jeton, clé SSH, registre).",
       "Vérifier/renouveler le secret côté plateforme. L'agent ne touche jamais aux secrets."),
    _r("out_of_memory", r"oomkilled|memoryerror|heap out of memory|cannot allocate memory",
       "exécution", 0.88, "open_pr",
       "Le processus a dépassé la mémoire allouée.",
       "Augmenter la limite mémoire du job/conteneur ou réduire la taille des données."),
    _r("deploy_failure", r"crashloopbackoff|readiness probe failed|health ?check failed|"
       r"imagepullbackoff|deployment .{0,40}failed",
       "déploiement", 0.88, "rollback",
       "Le déploiement a échoué (healthcheck, image ou crash au démarrage).",
       "Revenir à la dernière version saine (rollback), puis analyser les logs de démarrage."),
    _r("missing_dependency", r"no module named '?([\w\.\-]+)'?|cannot find module '([^']+)'|"
       r"no matching distribution found for ([\w\-\.=]+)|could not find a version that satisfies",
       "installation / tests", 0.92, "open_pr",
       "Dépendance absente ou introuvable.",
       "Ajouter ou corriger la dépendance « {detail} » dans requirements.txt / package.json."),
    _r("config_error", r"missing required environment variable|environment variable .{0,40}"
       r"(is not set|not defined)|invalid workflow file|yaml.{0,40}(error|invalid)|"
       r"keyerror: '[A-Z_]{3,}'",
       "configuration", 0.85, "open_pr",
       "Configuration erronée ou variable d'environnement manquante.",
       "Corriger la configuration (« {detail} ») et documenter la variable dans .env.example."),
    _r("lint_error", r"ruff.{0,40}found \d+ error|\bE\d{3}\b.{0,80}|\bF\d{3}\b.{0,80}|"
       r"eslint.{0,60}error|\d+ problems? \(\d+ errors?",
       "qualité (lint)", 0.84, "open_pr",
       "Le contrôle de style ou de qualité (lint) a échoué.",
       "Corriger les violations (ruff --fix / eslint --fix) et relancer."),
    _r("timeout_network", r"etimedout|econnreset|connection reset by peer|"
       r"temporary failure in name resolution|503 service unavailable|"
       r"read timed out|operation timed out",
       "réseau", 0.86, "rerun_job",
       "Échec transitoire (réseau ou service externe indisponible).",
       "Relancer le job ; si l'échec persiste, vérifier le service externe."),
    _r("build_error", r"npm err! code elifecycle|syntaxerror|compilation failed|"
       r"failed to solve|error: command .{0,60} failed",
       "build", 0.80, "open_pr",
       "Erreur de compilation ou de construction de l'image.",
       "Corriger l'erreur de syntaxe/build indiquée dans les preuves."),
    _r("test_failure", r"\d+ failed|failed [\w/\.\-]+::\w+|assertionerror|"
       r"tests? failed",
       "tests", 0.75, "none",
       "Un ou plusieurs tests échouent : correction fonctionnelle requise.",
       "Examiner le test en échec ; l'agent propose, un humain corrige."),
]


def _evidence(text: str, rule: Rule, limit: int = 3) -> tuple[list[str], str]:
    lines, detail = [], ""
    for line in text.splitlines():
        m = rule.pattern.search(line)
        if m:
            lines.append(line.strip()[:200])
            if not detail:
                detail = next((g for g in m.groups() if g), m.group(0))
            if len(lines) == limit:
                break
    return lines, detail


def analyze(raw_log: str, max_chars: int = 20000) -> Diagnosis:
    """Retourne un diagnostic ; s'abstient (confiance 0) si aucun signal."""
    text = prepare_log(raw_log, max_chars)
    for rule in RULES:
        evidence, detail = _evidence(text, rule)
        if evidence:
            boost = 0.04 if len(evidence) > 1 else 0.0
            return Diagnosis(
                category=rule.category,
                stage=rule.stage,
                confidence=round(min(rule.confidence + boost, 0.99), 2),
                explanation=rule.explanation,
                proposed_fix=rule.fix.format(detail=detail),
                recommended_action=rule.action,
                evidence=evidence,
            )
    return Diagnosis(
        category="unknown", stage="inconnue", confidence=0.0,
        explanation="Aucune signature d'erreur connue : abstention.",
        proposed_fix="Escalade vers un humain avec le log complet.",
        recommended_action="none", abstained=True,
    )
