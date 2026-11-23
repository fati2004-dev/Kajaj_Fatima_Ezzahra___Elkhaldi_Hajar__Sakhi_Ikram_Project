import pytest

from src.analyzer import analyze, redact


def test_missing_dependency():
    d = analyze("ModuleNotFoundError: No module named 'pandas'")
    assert d.category == "missing_dependency"
    assert "pandas" in d.proposed_fix
    assert d.recommended_action == "open_pr"


def test_network_error_suggests_rerun():
    assert analyze("curl: ETIMEDOUT").recommended_action == "rerun_job"


def test_unknown_log_abstains():
    d = analyze("something weird happened")
    assert d.abstained and d.confidence == 0.0 and d.recommended_action == "none"


def test_empty_log_rejected():
    with pytest.raises(ValueError):
        analyze("   ")


def test_long_log_keeps_the_tail():
    log = ("noise\n" * 50_000) + "ModuleNotFoundError: No module named 'x'"
    assert analyze(log, max_chars=1000).category == "missing_dependency"


def test_secrets_are_redacted():
    assert "abcdefghijklmnopqrstuvwxyz1234" not in redact("token=ghp_abcdefghijklmnopqrstuvwxyz1234")
