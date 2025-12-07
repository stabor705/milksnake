import pytest
from pathlib import Path
import tempfile
import yaml

from milksnake.config import Config

@pytest.fixture
def test_default_config():
    config = Config.from_defaults()
    assert config.port == 9161
    assert config.read_community == "public"
    assert config.write_community == "private"
    assert config.trap_community == "public"
    assert config.walkfile == "walkfile.txt"

@pytest.fixture
def test_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "port": 1161,
            "read_community": "test_read",
            "write_community": "test_write",
            "trap_community": "test_trap",
            "walkfile": "custom.txt"
        }, f)
        temp_path = f.name

    try:
        config = Config.from_file(temp_path)
        assert config.port == 1161
        assert config.read_community == "test_read"
        assert config.write_community == "test_write"
        assert config.trap_community == "test_trap"
        assert config.walkfile == "custom.txt"
    finally:
        Path(temp_path).unlink()


@pytest.fixture
def test_config_from_partial_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"port": 2000}, f)
        temp_path = f.name

    try:
        config = Config.from_file(temp_path)
        assert config.port == 2000
        assert config.read_community == "public"
    finally:
        Path(temp_path).unlink()

@pytest.fixture
def test_config_from_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = f.name

    try:
        config = Config.from_file(temp_path)
        assert config.port == 9161
        assert config.read_community == "public"
    finally:
        Path(temp_path).unlink()