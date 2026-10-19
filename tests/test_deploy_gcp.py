"""Exercise deployment configuration and provisioning without cloud writes or credentials."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("deploy_gcp", ROOT / "scripts/deploy_gcp.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    monkeypatch.setattr(os, "environ", {})
    (tmp_path / "deploy").mkdir()
    for filename in ("firestore.rules", "firestore.indexes.json"):
        (tmp_path / "deploy" / filename).write_bytes((ROOT / "deploy" / filename).read_bytes())
    file = tmp_path / ".env.deploy"
    file.write_text(
        "\n".join(
            [
                "PROJECT_ID=demo-optimiser",
                "OPT_FIRESTORE_DATABASE=optimiser-test",
                "GITHUB_APP_ID=123",
                "GITHUB_APP_SLUG=demo-app",
                "GITHUB_CLIENT_ID=public-client",
                "NEXT_PUBLIC_FIREBASE_API_KEY=public-key",
                "NEXT_PUBLIC_FIREBASE_PROJECT_ID=demo-optimiser",
                "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=demo-optimiser.firebaseapp.com",
                "NEXT_PUBLIC_FIREBASE_APP_ID=1:123:web:demo",
                "GOOGLE_API_KEY=private-key-do-not-print",
                "GITHUB_CLIENT_SECRET=private-oauth",
                'GITHUB_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\n'
                'fixture\\n-----END PRIVATE KEY-----"',
            ]
        )
        + "\n"
    )
    return file


def test_dry_run_has_no_cloud_calls_or_credential_disclosure(config, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["deploy", "--config", str(config), "--dry-run"])
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("Unexpected cloud call"))
    assert MODULE.main() == 0
    output = capsys.readouterr().out
    assert '"mutations": false' in output
    assert '"firestore_database": "optimiser-test"' in output
    assert "private-key-do-not-print" not in output and "private-oauth" not in output


def test_config_is_data_and_cannot_execute_shell(config, monkeypatch, tmp_path):
    marker = tmp_path / "executed"
    with config.open("a") as file:
        file.write(f"IGNORED=$(touch {marker})\n")
    c = MODULE.configuration(config)
    assert c["IGNORED"].startswith("$(touch") and not marker.exists()
    monkeypatch.setenv("PROJECT_ID", "different-project")
    with pytest.raises(MODULE.DeployError, match="same project"):
        MODULE.configuration(config)


def test_no_default_cloud_project_or_overlapping_secrets(config):
    config.write_text(
        "\n".join(
            line for line in config.read_text().splitlines() if not line.startswith("PROJECT_ID=")
        )
        + "\n"
    )
    with pytest.raises(MODULE.DeployError, match="PROJECT_ID"):
        MODULE.configuration(config)
    config.write_text(config.read_text() + "PROJECT_ID=demo-optimiser\n")
    c = MODULE.configuration(config)
    c["MODEL_SECRET_RESOURCE"] = "your-optimiser-app-key"
    with pytest.raises(MODULE.DeployError, match="distinct"):
        MODULE.secret_specs(c)


@pytest.mark.parametrize("database", ["", "bad/name", "UPPERCASE", "abc"])
def test_deployment_requires_an_explicit_valid_database(config, database):
    config.write_text(
        config.read_text().replace(
            "OPT_FIRESTORE_DATABASE=optimiser-test", "OPT_FIRESTORE_DATABASE=" + database
        )
    )
    with pytest.raises(MODULE.DeployError, match="OPT_FIRESTORE_DATABASE"):
        MODULE.configuration(config)


class FakeCloud:
    def __init__(self, existing):
        self.existing = existing
        self.calls = []
        self.uploads = []
        self.runtime_environments = []

    def exists(self, *args):
        self.calls.append(("exists", args, None))
        return self.existing

    def grant(self, account, role):
        self.calls.append(("grant", (account, role), None))

    def run(self, *args, stdin=None):
        self.calls.append(("run", args, stdin))
        if args[:2] == ("projects", "describe"):
            return "123456789"
        if args[:3] == ("run", "services", "describe"):
            return "https://your-optimiser-123456789.us-central1.run.app"
        if args[:2] == ("builds", "submit"):
            path = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--config="))
            self.uploads.append(json.loads(Path(path).read_text()))
        if args[:2] == ("run", "deploy"):
            path = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--env-vars-file="))
            self.runtime_environments.append(yaml.safe_load(Path(path).read_text()))
        return ""


@pytest.mark.parametrize("existing", [False, True])
def test_provisioning_preserves_keys_and_creates_one_service(config, monkeypatch, existing):
    c = MODULE.configuration(config)
    cloud = FakeCloud(existing)
    firebase_deployments = []

    def firebase_run(args, **kwargs):
        assert args[:2] == ["firebase", "deploy"]
        file = Path(args[args.index("--config") + 1])
        firebase_config = json.loads(file.read_text())
        for entry in firebase_config["firestore"]:
            for key in ("rules", "indexes"):
                path = file.parent / entry[key]
                assert path.is_file() and path.is_relative_to(file.parent)
        firebase_deployments.append(firebase_config)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", firebase_run)
    client = SimpleNamespace(
        get=lambda url: SimpleNamespace(
            status_code=200, json=lambda: {"status": "ready"}, text="Your Optimiser"
        )
    )
    monkeypatch.setattr(MODULE.httpx, "Client", lambda **k: SimpleContext(client))
    MODULE.deploy(c, cloud)
    commands = [args for kind, args, _ in cloud.calls if kind == "run"]
    deployments = [args for args in commands if args[:2] == ("run", "deploy")]
    assert len(deployments) == 1
    assert cloud.runtime_environments[0]["OPT_FIRESTORE_DATABASE"] == "optimiser-test"
    assert "--min-instances=0" in deployments[0] and "--max-instances=1" in deployments[0]
    assert not any(args[:2] == ("run", "jobs") for args in commands)
    creates = [item for item in cloud.calls if item[1][:2] == ("secrets", "create")]
    assert len(creates) == (0 if existing else 5)
    assert not any("versions" in args and "add" in args for args in commands)
    serialized = json.dumps(cloud.uploads)
    assert "private-key-do-not-print" not in serialized and "private-oauth" not in serialized
    assert "NEXT_PUBLIC_FIREBASE_API_KEY=public-key" in serialized
    assert any("--max-concurrent-dispatches=1" in args for args in commands)
    database_commands = [
        args for _, args, _ in cloud.calls if args[:2] == ("firestore", "databases")
    ]
    assert database_commands
    assert all("--database=optimiser-test" in args for args in database_commands)
    assert not any("(default)" in arg for args in database_commands for arg in args)
    assert [entry["database"] for entry in firebase_deployments[0]["firestore"]] == [
        "optimiser-test"
    ]
    assert firebase_deployments[0]["firestore"][0]["database"] != "(default)"


class SimpleContext:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, *_):
        pass


def test_resource_inspection_does_not_treat_permission_errors_as_missing(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stderr="PERMISSION_DENIED: cannot inspect this secret",
        ),
    )
    with pytest.raises(MODULE.DeployError, match="Could not inspect resource"):
        MODULE.Cloud("demo-optimiser").exists("secrets", "describe", "fixture")


def test_missing_initial_secret_stops_before_build_or_service_creation(config):
    c = MODULE.configuration(config)
    c.pop("GOOGLE_API_KEY")
    cloud = FakeCloud(False)
    with pytest.raises(MODULE.DeployError, match="OPT_MANAGED_API_KEY"):
        MODULE.deploy(c, cloud)
    assert not any(
        args[:2] in {("secrets", "create"), ("run", "deploy"), ("builds", "submit")}
        for kind, args, _ in cloud.calls
        if kind == "run"
    )


@pytest.mark.parametrize(
    "message",
    [
        "NOT_FOUND: queue not found",
        "Cannot find service [your-optimiser]",
        "Could not find the requested resource",
        "Bucket does not exist",
    ],
)
def test_missing_resource_messages_support_first_deploy(monkeypatch, message):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stderr=message,
        ),
    )
    assert not MODULE.Cloud("demo-optimiser").exists("run", "services", "describe", "fixture")
