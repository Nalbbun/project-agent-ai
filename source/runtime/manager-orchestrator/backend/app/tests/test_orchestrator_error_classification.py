from app.services.orchestrator import OrchestratorService


def test_transient_error_classification():
    assert OrchestratorService._classify_error(Exception('connection timeout to router')) == 'transient'
    assert OrchestratorService._classify_error(Exception('schema_validation failed')) == 'permanent'
