"""Do not admit traffic until both HTTP backends work; fail closed on startup errors."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "combined_entrypoint", ROOT / "deploy/combined-entrypoint.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


@pytest.fixture
def clock(monkeypatch):
    value = [0.0]
    monkeypatch.setattr(MODULE.time, "monotonic", lambda: value[0])

    def sleep(seconds):
        value[0] += seconds

    monkeypatch.setattr(MODULE.time, "sleep", sleep)
    return value


def test_waits_for_http_readiness_of_both_upstreams(monkeypatch, clock):
    calls = []

    def request(url, timeout):
        calls.append(url)
        if ":8000/" in url and calls.count(url) < 3:
            raise URLError("API is still starting")
        return Response()

    monkeypatch.setattr(MODULE, "urlopen", request)
    children = [SimpleNamespace(poll=lambda: None), SimpleNamespace(poll=lambda: None)]
    assert MODULE.wait_for_backends(children, lambda: False, timeout=2)
    assert calls.count("http://127.0.0.1:8000/api/v1/health") == 3
    assert calls.count("http://127.0.0.1:3000/") == 1
    assert clock[0] >= 0.4


def test_backend_unavailable_times_out_without_opening_ingress(monkeypatch, clock, capsys):
    monkeypatch.setattr(MODULE, "urlopen", lambda *a, **k: Response())
    Response.status = 503
    try:
        assert not MODULE.wait_for_backends([], lambda: False, timeout=1)
    finally:
        Response.status = 200
    assert 1 <= clock[0] < 2
    assert "timed out" in capsys.readouterr().err


@pytest.mark.parametrize("exit_code, cancelled", [(1, False), (None, True)])
def test_crashed_child_or_shutdown_aborts_startup(monkeypatch, clock, exit_code, cancelled):
    monkeypatch.setattr(MODULE, "urlopen", lambda *a, **k: pytest.fail("Startup should abort"))
    assert not MODULE.wait_for_backends(
        [SimpleNamespace(poll=lambda: exit_code)], lambda: cancelled
    )
