"""First-time setup uses a real temporary Git repo and no network/model credentials."""

import json
import os
import subprocess
from pathlib import Path

from seo_optimizer.local import cron_line, main


def repository(root: Path) -> Path:
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    (root / "index.html").write_text("<html><head><title>Example</title></head></html>")
    subprocess.run(["git", "-C", str(root), "add", "index.html"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test Owner",
            "-c",
            "user.email=owner@example.test",
            "commit",
            "-m",
            "Initial page",
        ],
        check=True,
        capture_output=True,
    )
    return root


def test_first_run_and_idempotent_resume(tmp_path: Path, monkeypatch) -> None:
    repo = repository(tmp_path / "site with spaces")
    config = tmp_path / "launcher.json"
    data = tmp_path / "private data"
    monkeypatch.setenv("SETUP_TEST_PASSWORD", "correct-horse-example-password")
    before = os.environ.get("OPT_DATA_DIR")
    command = [
        "--no-start",
        "--config",
        str(config),
        "--data-dir",
        str(data),
        "--repo",
        str(repo),
        "--url",
        "https://example.test",
        "--provider",
        "rules",
        "--password-env",
        "SETUP_TEST_PASSWORD",
    ]
    assert main(command) == 0
    first = config.read_text()
    assert "correct-horse" not in first
    assert config.stat().st_mode & 0o777 == 0o600
    assert (data / "secret.key").stat().st_mode & 0o777 == 0o600
    assert main(["--no-start", "--config", str(config)]) == 0
    assert config.read_text() == first
    assert os.environ.get("OPT_DATA_DIR") == before
    value = json.loads(first)
    assert value["repo_root"] == str(repo)


def test_invalid_inputs_do_not_save_setup(tmp_path: Path, monkeypatch) -> None:
    repo = repository(tmp_path / "site")
    monkeypatch.setenv("SETUP_TEST_PASSWORD", "short")
    config = tmp_path / "launcher.json"
    assert (
        main(
            [
                "--no-start",
                "--config",
                str(config),
                "--data-dir",
                str(tmp_path / "data"),
                "--repo",
                str(repo),
                "--url",
                "https://example.test",
                "--provider",
                "rules",
                "--password-env",
                "SETUP_TEST_PASSWORD",
            ]
        )
        == 1
    )
    assert not config.exists()


def test_cron_quotes_spaces_metacharacters_and_percent(tmp_path: Path) -> None:
    root = tmp_path / "install's 100% local"
    line = cron_line(root / "private.json", root)
    assert line.startswith("*/5 * * * * cd ")
    assert "\\%" in line
    assert "'\"'\"'" in line
    assert "--once" in line
    assert "your-optimiser:" in line
