"""
PII detection and redaction, applied before any claim text reaches the LLM.
"""
import re

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

TARGET_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "US_SSN",
    "CREDIT_CARD",
    "LOCATION",
]

OPERATORS = {
    "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
    **{e: OperatorConfig("replace", {"new_value": f"<{e}>"}) for e in TARGET_ENTITIES},
}

POLICY_NUMBER_PATTERN = re.compile(r"^[A-Za-z]-\d+$")

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()


def redact(text: str) -> tuple[str, list[dict]]:
    results = _analyzer.analyze(text=text, entities=TARGET_ENTITIES, language="en")

    filtered_results = [
        r for r in results if not POLICY_NUMBER_PATTERN.match(text[r.start:r.end])
    ]

    anonymized = _anonymizer.anonymize(text=text, analyzer_results=filtered_results, operators=OPERATORS)
    found = [
        {"entity_type": r.entity_type, "start": r.start, "end": r.end, "score": round(r.score, 2)}
        for r in filtered_results
    ]
    return anonymized.text, found