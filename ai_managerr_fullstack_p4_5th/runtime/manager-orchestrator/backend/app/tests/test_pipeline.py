from app.services.orchestrator import PIPELINE


def test_pipeline_order():
    phases = [step["phase"] for step in PIPELINE]
    assert phases[0] == "manager-plan"
    assert phases[-1] == "manager-merge"
    assert "pm" in phases and "architect" in phases and "qa" in phases and "secops" in phases


def test_pipeline_dependencies_present():
    phase_set = {step["phase"] for step in PIPELINE}
    for step in PIPELINE:
        for dependency in step["depends_on"]:
            assert dependency in phase_set
