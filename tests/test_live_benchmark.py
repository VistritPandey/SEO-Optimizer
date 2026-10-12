import json
from pathlib import Path

from seo_optimizer.live_benchmark import benchmark
from seo_optimizer.llm import ProviderError

CASES = Path(__file__).parent / "fixtures/cases.json"


def test_hybrid_reports_when_rules_avoid_inference(tmp_path, monkeypatch):
    class NoInference:
        def __init__(self, *args, **kwargs):
            pass

        def complete(self, *args, **kwargs):
            raise AssertionError("A supported rules case must not incur inference")

        def close(self):
            pass

    monkeypatch.setattr("seo_optimizer.live_benchmark.ModelClient", NoInference)
    output = tmp_path / "hybrid.json"
    assert benchmark(CASES, output, "ollama", "controlled-model", 1, arm="hybrid") == 0
    protocol = json.loads(output.with_suffix(".protocol.json").read_text())
    assert protocol["inference_cases"] == 0 and protocol["arm"] == "hybrid"
    report = json.loads(output.read_text())
    assert report["counts"] == {"passed": 1, "failed": 0, "skipped": 0}
    assert "0/1" in report["unverified"][0]


def test_real_run_error_is_failed_and_model_never_receives_answers(tmp_path, monkeypatch):
    requests = []

    class FailingProvider:
        def __init__(self, *args, **kwargs):
            pass

        def complete(self, instructions, request, *args, **kwargs):
            requests.append(request)
            raise ProviderError("Controlled provider outage")

        def close(self):
            pass

    monkeypatch.setattr("seo_optimizer.live_benchmark.ModelClient", FailingProvider)
    output = tmp_path / "failed.json"
    assert benchmark(CASES, output, "ollama", "controlled-model", 1) == 1
    assert "expected" not in requests[0] and "split" not in requests[0]
    assert "case_id" not in requests[0]
    report = json.loads(output.read_text())
    assert report["counts"]["failed"] == 1 and report["counts"]["skipped"] == 0
    assert "provider outage" in report["results"][0]["failures"][0]
