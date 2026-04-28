from app.services.worker_service import WorkerService


class _FakeExecResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self):
        self.items = []

    def exec(self, stmt):
        return _FakeExecResult(self.items)

    def add(self, item):
        if item not in self.items:
            self.items.append(item)

    def commit(self):
        return None

    def refresh(self, item):
        return None


def test_worker_heartbeat_upserts_record():
    session = _FakeSession()
    service = WorkerService(session, worker_id='w1')
    worker = service.heartbeat(status='idle')
    assert worker.worker_id == 'w1'
    worker2 = service.heartbeat(status='processing')
    assert worker2.status == 'processing'
