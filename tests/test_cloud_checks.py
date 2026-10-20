"""Cloud request validation; live cloud execution is a separate integration stage."""

import io
import tarfile
from pathlib import Path

import pytest
from pydantic import HttpUrl

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.cloud_checks import SCOPE, archive_source, build_config, verification_scope


def test_archive_omits_control_secrets_and_normalizes_permissions(tmp_path: Path) -> None:
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<title>Example</title>")
    (tmp_path / ".env").write_text("private-value")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("private-remote")
    with tarfile.open(fileobj=io.BytesIO(archive_source(tmp_path)), mode="r:gz") as archive:
        assert archive.getnames() == ["web/index.html"]
        assert archive.getmember("web/index.html").mode == 0o644
    (tmp_path / "link").symlink_to(tmp_path / "web" / "index.html")
    with pytest.raises(ValueError, match="symlink"):
        archive_source(tmp_path)


def test_cloud_checks_are_arg_lists_without_credentials_or_host_access() -> None:
    spec = ProjectSpec(
        name="Example",
        website_url=HttpUrl("https://example.test"),
        check_commands=[["python", "verify_site.py"]],
    )
    config = build_config(
        spec,
        "example-project",
        "source-bucket",
        "source.tar.gz",
        "checks@example-project.iam.gserviceaccount.com",
        "tenant",
        "job",
    )
    args = config["steps"][0]["args"]
    assert args[args.index("--network") + 1] == "none"
    assert "--read-only" in args
    assert args[-3:] == ["python:3.12-slim", "python", "verify_site.py"]
    assert "readonly" in args[args.index("--mount") + 1]
    assert not any("secret" in str(key).lower() for key in config)
    assert "env" not in config["steps"][0]
    assert config["options"]["logging"] == "CLOUD_LOGGING_ONLY"


def test_cloud_config_validates_against_actual_sdk() -> None:
    sdk = pytest.importorskip("google.cloud.devtools.cloudbuild_v1")
    spec = ProjectSpec(
        name="Example",
        website_url=HttpUrl("https://example.test"),
        check_commands=[["python", "verify_site.py"]],
    )
    config = build_config(
        spec,
        "example-project",
        "source-bucket",
        "source.tar.gz",
        "checks@example-project.iam.gserviceaccount.com",
        "tenant",
        "job",
    )
    actual = sdk.Build(config)
    assert actual.source.storage_source.object_ == "source.tar.gz"
    assert actual.timeout.seconds == 180
    assert actual.steps[0].args[-1] == "verify_site.py"


def test_verification_context_does_not_leak_between_jobs() -> None:
    assert SCOPE.get() is None
    with verification_scope("tenant-one", "job-one"):
        first = SCOPE.get()
        assert first is not None
        first.count += 1
        with verification_scope("tenant-two", "job-two"):
            assert SCOPE.get().count == 0
        assert SCOPE.get() is first
    assert SCOPE.get() is None


@pytest.mark.parametrize("poll_error", [False, True])
def test_regional_polling_retains_source_until_build_finishes(tmp_path, monkeypatch, poll_error):
    from unittest.mock import Mock

    sdk = pytest.importorskip("google.cloud.devtools.cloudbuild_v1")
    storage = pytest.importorskip("google.cloud.storage")
    from google.api_core.exceptions import NotFound

    from seo_optimizer.cloud_checks import verify_cloud

    for name, value in {
        "GOOGLE_CLOUD_PROJECT": "example-project",
        "OPT_BUILD_BUCKET": "source-bucket",
        "OPT_BUILD_ACCOUNT": "checks@example-project.iam.gserviceaccount.com",
        "OPT_BUILD_REGION": "us-central1",
    }.items():
        monkeypatch.setenv(name, value)
    source = Mock()
    storage_client = Mock()
    storage_client.bucket.return_value.blob.return_value = source
    monkeypatch.setattr(storage, "Client", lambda **kwargs: storage_client)
    build_client = Mock()
    operation = build_client.create_build.return_value
    if poll_error:
        operation.result.side_effect = NotFound("Regional operation not found")
    else:
        operation.result.return_value = sdk.Build(status=sdk.Build.Status.SUCCESS, id="build")
    options = []

    def client(**kwargs):
        options.append(kwargs["client_options"])
        return build_client

    monkeypatch.setattr(sdk, "CloudBuildClient", client)
    (tmp_path / "index.html").write_text("<title>Example</title>")
    spec = ProjectSpec(
        name="Example", website_url="https://example.test/", check_commands=[["python", "check.py"]]
    )
    with verification_scope("tenant", "job"):
        if poll_error:
            with pytest.raises(ValueError, match="unavailable"):
                verify_cloud(tmp_path, spec)
            source.delete.assert_not_called()
        else:
            result = verify_cloud(tmp_path, spec)
            assert result[0]["passed"]
            source.delete.assert_called_once()
    assert options == [{"api_endpoint": "us-central1-cloudbuild.googleapis.com"}]
    storage_client.close.assert_called_once()
    build_client.transport.close.assert_called_once()
