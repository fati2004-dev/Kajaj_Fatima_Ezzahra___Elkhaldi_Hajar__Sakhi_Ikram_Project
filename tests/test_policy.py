from src.config import get_settings
from src.policy import decide


def test_rollback_always_needs_approval():
    d = decide("rollback", 0.99, 0, get_settings())
    assert d.requires_approval and not d.auto_allowed


def test_low_confidence_needs_approval():
    assert decide("rerun_job", 0.3, 0, get_settings()).requires_approval


def test_rerun_auto_when_confident():
    assert decide("rerun_job", 0.9, 0, get_settings()).auto_allowed


def test_rerun_blocked_after_max_retries():
    s = get_settings()
    assert decide("rerun_job", 0.9, s.max_retries, s).requires_approval
