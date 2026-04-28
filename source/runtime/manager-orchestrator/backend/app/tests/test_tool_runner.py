from pathlib import Path

from app.services.tool_runner import ToolRunner
from app.services.vector_store import VectorStoreService


def test_tool_runner_materializes_dev_files(tmp_path: Path):
    runner = ToolRunner(tmp_path)
    payload = {
        'files': [{'path': 'app/main.py', 'content': 'def main():\n    return 1\n'}],
        'tests': [{'path': 'test_main.py', 'content': 'from app.main import main\n\ndef test_main():\n    assert main() == 1\n'}],
    }
    build = runner.run_build('run-1', 'dev-be', payload)
    lint = runner.run_lint('run-1', 'dev-be', payload)
    assert build['status'] == 'pass'
    assert lint['status'] == 'pass'
    assert (tmp_path / 'workspaces' / 'run-1' / 'workspace' / 'app' / 'main.py').exists()


def test_tool_runner_scan_reports_secret_hit(tmp_path: Path):
    runner = ToolRunner(tmp_path)
    payload = {
        'files': [{'path': 'settings.py', 'content': 'API_KEY = "secret-value"\n'}],
    }
    report = runner.run_scan('run-2', 'secops', payload)
    assert report['secret_findings']
    assert report['status'] in {'warn', 'fail', 'pass'}


def test_vector_store_embed_text_returns_fixed_dimension():
    service = VectorStoreService()
    vector = service.embed_text('approval workflow auth policy')
    assert len(vector) == 256
    assert any(value != 0 for value in vector)
