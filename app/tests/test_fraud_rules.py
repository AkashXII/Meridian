"""
Tests for the deterministic fraud checks. Dates are computed relative to
today, not hardcoded — a hardcoded incident_date would silently drift past
the 60-day deadline as real time passes, breaking these tests months from
now for a reason that has nothing to do with the code.
"""
from datetime import date, timedelta

from app.fraud_rules import run_fraud_checks
from app.models import ExtractedClaim


def make_claim(**overrides):
    """A minimal valid, non-flagged claim — override only what a test needs."""
    defaults = dict(
        policy_number="A-12345",
        claim_type="auto",
        incident_date=(date.today() - timedelta(days=10)).isoformat(),
        description="test claim",
        amount_requested=1000.0,
    )
    defaults.update(overrides)
    return ExtractedClaim(**defaults)


def test_clean_claim_has_no_violations():
    assert run_fraud_checks(make_claim()) == []


def test_health_prefix_on_non_health_claim_is_flagged():
    violations = run_fraud_checks(make_claim(policy_number="H-99999", claim_type="auto"))
    assert len(violations) == 1
    assert "H-" in violations[0]


def test_health_claim_without_h_prefix_is_flagged():
    violations = run_fraud_checks(make_claim(policy_number="A-99999", claim_type="health"))
    assert len(violations) == 1
    assert "H-" in violations[0]


def test_health_claim_with_h_prefix_is_clean():
    assert run_fraud_checks(make_claim(policy_number="H-99999", claim_type="health")) == []


def test_claim_filed_within_deadline_is_clean():
    claim = make_claim(incident_date=(date.today() - timedelta(days=30)).isoformat())
    assert run_fraud_checks(claim) == []


def test_claim_filed_past_deadline_is_flagged():
    claim = make_claim(incident_date=(date.today() - timedelta(days=90)).isoformat())
    violations = run_fraud_checks(claim)
    assert any("deadline" in v for v in violations)


def test_future_incident_date_is_flagged():
    claim = make_claim(incident_date=(date.today() + timedelta(days=5)).isoformat())
    violations = run_fraud_checks(claim)
    assert any("future" in v for v in violations)


def test_malformed_date_is_flagged_not_crashed():
    violations = run_fraud_checks(make_claim(incident_date="not-a-date"))
    assert any("valid" in v for v in violations)


def test_missing_incident_date_skips_deadline_check():
    violations = run_fraud_checks(make_claim(incident_date=None))
    assert not any("deadline" in v or "future" in v for v in violations)


def test_zero_amount_is_flagged():
    violations = run_fraud_checks(make_claim(amount_requested=0.0))
    assert any("valid claim amount" in v for v in violations)


def test_negative_amount_is_flagged():
    violations = run_fraud_checks(make_claim(amount_requested=-50.0))
    assert any("valid claim amount" in v for v in violations)


def test_positive_amount_is_clean():
    assert run_fraud_checks(make_claim(amount_requested=250.0)) == []


def test_multiple_violations_all_reported():
    """Regression test for the exact bug we hit live: an H-prefixed policy
    on a non-health claim, filed late, with a zero amount — should catch
    all three, not stop at the first one found."""
    claim = make_claim(
        policy_number="H-1",
        claim_type="auto",
        incident_date=(date.today() - timedelta(days=90)).isoformat(),
        amount_requested=0.0,
    )
    assert len(run_fraud_checks(claim)) == 3