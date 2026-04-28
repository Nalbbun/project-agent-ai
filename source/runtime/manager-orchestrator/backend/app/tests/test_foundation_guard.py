from app.services.foundation_guard import FOUNDATION_GUARD_CODES


def test_foundation_guard_codes_cover_must_keep_items():
    assert FOUNDATION_GUARD_CODES == [
        "router-role-routing",
        "queue-worker-retry-dead-letter",
        "approval-rbac-project-membership",
        "artifact-event-audit-replay",
        "rag-project-knowledge-reindex",
        "runner-sandbox-isolation",
    ]
