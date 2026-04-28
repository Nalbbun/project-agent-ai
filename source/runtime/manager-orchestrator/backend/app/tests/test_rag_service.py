from types import SimpleNamespace
from uuid import uuid4

from app.services.rag_service import RagService


class _FakeExecResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows_by_model):
        self.rows_by_model = rows_by_model

    def exec(self, stmt):
        model_name = stmt.column_descriptions[0]["type"].__name__
        return _FakeExecResult(self.rows_by_model.get(model_name, []))


def test_rag_service_prefers_project_knowledge():
    doc = SimpleNamespace(
        project_id=uuid4(),
        title='API Guide',
        source_type='doc',
        tags=['api', 'auth'],
        content='Use JWT auth and approval API for project workflow',
        summary='approval api guide',
    )
    session = _FakeSession({'ProjectKnowledge': [doc], 'Artifact': []})
    rag = RagService(session)
    results = rag.retrieve(doc.project_id, 'architect', 'approval api auth', top_k=3)
    assert results
    assert results[0]['source_type'] == 'project-knowledge'
