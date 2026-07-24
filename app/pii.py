
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

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()


def redact(text: str) -> tuple[str, list[dict]]:

    results = _analyzer.analyze(
        text=text, entities=TARGET_ENTITIES, language="en"
    )
    anonymized = _anonymizer.anonymize(
        text=text, analyzer_results=results, operators=OPERATORS
    )
    found = [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(r.score, 2),
        }
        for r in results
    ]
    return anonymized.text, found