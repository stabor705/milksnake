import tempfile
from pathlib import Path

import yaml

from milksnake.config import Config


def test_default_config():
    # Arrange & Act
    config = Config.from_defaults()

    # Assert
    assert config.interface == "127.0.0.1"
    assert config.port == 9161
    assert config.read_community == "public"
    assert config.write_community == "private"
    assert config.trap_community == "public"
    assert config.walkfiles == ["walkfile.txt"]


def test_config_from_file():
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "interface": "0.0.0.0",
                "port": 1161,
                "read_community": "test_read",
                "write_community": "test_write",
                "trap_community": "test_trap",
                "walkfiles": ["custom1.txt", "custom2.txt"],
            },
            f,
        )
        temp_path = f.name

    try:
        # Act
        config = Config.from_file(temp_path)

        # Assert
        assert config.interface == "0.0.0.0"
        assert config.port == 1161
        assert config.read_community == "test_read"
        assert config.write_community == "test_write"
        assert config.trap_community == "test_trap"
        assert config.walkfiles == ["custom1.txt", "custom2.txt"]
    finally:
        Path(temp_path).unlink()


def test_config_from_partial_file():
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"port": 2000}, f)
        temp_path = f.name

    try:
        # Act
        config = Config.from_file(temp_path)

        # Assert
        assert config.port == 2000
        assert config.interface == "127.0.0.1"
        assert config.read_community == "public"
        assert config.walkfiles == ["walkfile.txt"]
    finally:
        Path(temp_path).unlink()


def test_config_from_empty_file():
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = f.name

    try:
        # Act
        config = Config.from_file(temp_path)

        # Assert
        assert config.interface == "127.0.0.1"
        assert config.port == 9161
        assert config.read_community == "public"
        assert config.walkfiles == ["walkfile.txt"]
    finally:
        Path(temp_path).unlink()


def test_config_multiple_walkfiles():
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"walkfiles": ["file1.txt", "file2.txt", "file3.txt"]}, f)
        temp_path = f.name

    try:
        # Act
        config = Config.from_file(temp_path)

        # Assert
        assert config.walkfiles == ["file1.txt", "file2.txt", "file3.txt"]
    finally:
        Path(temp_path).unlink()


def test_config_ipv6_interface():
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"interface": "::1", "port": 9161}, f)
        temp_path = f.name

    try:
        # Act
        config = Config.from_file(temp_path)

        # Assert
        assert config.interface == "::1"
    finally:
        Path(temp_path).unlink()
