from app.services.schema_validator import SchemaValidator


validator = SchemaValidator()


def test_pm_schema_required_keys():
    ok, errors = validator.validate("pm", {"summary": "s"})
    assert not ok
    assert errors


def test_architect_schema_passes():
    ok, errors = validator.validate(
        "architect",
        {
            "architecture_style": "modular monolith",
            "components": [],
            "apis": [],
            "database": {},
            "sequence": [],
            "adrs": [],
        },
    )
    assert ok
    assert errors == []
