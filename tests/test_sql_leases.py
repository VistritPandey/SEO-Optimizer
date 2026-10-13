"""Force the live-query/claim race between two workers on different queued jobs."""

import threading
from pathlib import Path

from pydantic import HttpUrl
from sqlalchemy import event

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store


def test_project_lease_arbitrates_stale_live_query(tmp_path: Path):
    store = Store(Settings(tmp_path, f"sqlite:///{tmp_path / 'queue.db'}", "test-secret"))
    owner, _ = store.create_user("owner@example.test", "hash")
    project = store.create_project(
        owner.id,
        ProjectCreate(spec=ProjectSpec(name="Site", website_url=HttpUrl("https://example.test"))),
    )
    store.enqueue(owner.id, project.id, "audit", "second-job", {})
    barrier = threading.Barrier(2)
    winner_done = threading.Event()
    result = {}
    errors = []

    def delay_second(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT jobs.project_id"):
            barrier.wait(timeout=10)
            if threading.current_thread().name == "second":
                assert winner_done.wait(timeout=10)

    event.listen(store.engine, "after_cursor_execute", delay_second)

    def claim(name):
        try:
            result[name] = store.claim(name, owner.id)
        except Exception as error:
            errors.append(error)
        finally:
            if name == "first":
                winner_done.set()

    threads = [
        threading.Thread(target=claim, args=(name,), name=name) for name in ("first", "second")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    event.remove(store.engine, "after_cursor_execute", delay_second)
    assert not errors, errors
    assert all(not thread.is_alive() for thread in threads)
    assert result["first"] is not None
    assert result["second"] is None
    first = result["first"]
    store.finish(owner.id, first.id, "first", "complete", {})
    assert store.claim("next", owner.id) is not None
    store.close()
