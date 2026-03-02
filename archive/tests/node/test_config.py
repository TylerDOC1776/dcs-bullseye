import json
import os
from pathlib import Path

import pytest

from node.node_service.config import ConfigError, load_config


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _base_config(**overrides):
    data = {
        "node_id": "test-node",
        "role": "server",
        "vps_endpoint": "https://example.com",
        "api_key": "abc123",
        "instances": [
            {
                "name": "TestInstance",
                "cmd_key": "test",
                "exe_path": "C:/DCS/Test/bin/DCS_server.exe",
                "log_path": "C:/Logs/test.log",
            }
        ],
    }
    data.update(overrides)
    return data


def test_load_config_basic(tmp_path):
    cfg_path = _write_config(tmp_path, _base_config())
    cfg = load_config(cfg_path)
    assert cfg.node_id == "test-node"
    assert cfg.api_key == "abc123"
    assert cfg.command_transport == "filesystem"
    assert cfg.instances[0].cmd_key == "test"


def test_load_config_api_key_from_file(tmp_path):
    key_file = tmp_path / "key.txt"
    key_file.write_text("secret-token\n", encoding="utf-8")
    data = _base_config(api_key=None, api_key_file=str(key_file))
    cfg_path = _write_config(tmp_path, data)
    cfg = load_config(cfg_path)
    assert cfg.api_key == "secret-token"


def test_load_config_api_key_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("NODE_TOKEN", "env-secret")
    data = _base_config(api_key=None, api_key_env="NODE_TOKEN")
    cfg_path = _write_config(tmp_path, data)
    cfg = load_config(cfg_path)
    assert cfg.api_key == "env-secret"


def test_invalid_role(tmp_path):
    cfg_path = _write_config(tmp_path, _base_config(role="invalid"))
    with pytest.raises(ConfigError):
        load_config(cfg_path)


def test_http_transport_requires_endpoint(tmp_path):
    cfg_path = _write_config(
        tmp_path,
        _base_config(command_transport="http", vps_endpoint="", api_key="abc"),
    )
    with pytest.raises(ConfigError):
        load_config(cfg_path)
