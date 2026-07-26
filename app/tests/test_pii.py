"""
Tests for redact(). These call the real Presidio analyzer/anonymizer (no
mocking) since the whole risk here is a real false positive or false
negative from the actual NLP model, not from our wrapper code.
"""
from app.pii import redact


def test_redacts_person_and_phone():
    text = "My name is John Smith, my number is 555-123-4567."
    redacted, found = redact(text)

    assert "John Smith" not in redacted
    assert "555-123-4567" not in redacted
    assert "<PERSON>" in redacted
    assert "<PHONE_NUMBER>" in redacted

    entity_types = {e["entity_type"] for e in found}
    assert "PERSON" in entity_types
    assert "PHONE_NUMBER" in entity_types


def test_policy_number_and_amount_survive_redaction():
    """Regression test: the whole reason TARGET_ENTITIES is narrow — a
    policy number or dollar amount must never be caught by a PII
    recognizer, since fraud_rules.py depends on reading these unmodified."""
    text = "Policy number is A-88213, claiming $3200 for repairs."
    redacted, _ = redact(text)

    assert "A-88213" in redacted
    assert "$3200" in redacted


def test_clean_text_has_no_entities_found():
    text = "Car hit while parked outside my house on 2026-06-14."
    redacted, found = redact(text)

    assert found == []
    assert redacted == text