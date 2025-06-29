"""Pytest configuration and shared fixtures for BitCrafty-Extractor tests."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock
import yaml

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def logger():
    """Create a logger for testing."""
    try:
        import structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.dev.ConsoleRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        return structlog.get_logger(__name__)
    except ImportError:
        return Mock()


@pytest.fixture
def mock_logger():
    """Create a mock logger for unit tests."""
    return Mock()


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        'ai': {
            'default_provider': 'openai_gpt4v',
            'fallback_provider': 'anthropic_claude',
            'openai': {
                'api_key': 'test_openai_key',
                'model': 'gpt-4-vision-preview',
                'timeout': 30.0
            },
            'anthropic': {
                'api_key': 'test_anthropic_key',
                'model': 'claude-3-sonnet-20240229',
                'timeout': 30.0
            }
        },
        'hotkeys': {
            'queue_screenshot': 'ctrl+shift+e',
            'analyze_queue': 'ctrl+shift+x',
            'enabled': True
        },
        'capture': {
            'target_process': 'bitcraft.exe',
            'game_window_patterns': ['BitCraft'],
            'min_window_width': 800,
            'min_window_height': 600,
            'focus_based_capture': True,
            'format': 'PNG',
            'quality': 95,
            'auto_detect_game_window': True
        }
    }


@pytest.fixture
def config_file_path(tmp_path, sample_config_data):
    """Create a temporary config file for testing."""
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config_data, f)
    return config_path


@pytest.fixture
def mock_config_manager(sample_config_data):
    """Create a mock config manager for testing."""
    from types import SimpleNamespace
    
    def dict_to_namespace(d):
        if isinstance(d, dict):
            return SimpleNamespace(**{k: dict_to_namespace(v) for k, v in d.items()})
        return d
    
    config_manager = Mock()
    config_manager.config = dict_to_namespace(sample_config_data)
    return config_manager


@pytest.fixture
def test_data_path():
    """Path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_screenshot():
    """Create sample screenshot data for testing."""
    try:
        import numpy as np
        return np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    except ImportError:
        pytest.skip("numpy not available for screenshot generation")


@pytest.fixture
def sample_ai_response():
    """Sample AI response for testing."""
    return {
        "items": [
            {
                "name": "Iron Ore",
                "tier": 1,
                "rarity": "common",
                "description": "Basic mining resource",
                "uses": ["smelting", "crafting"],
                "confidence": 0.95
            }
        ],
        "crafts": [
            {
                "name": "Iron Ingot",
                "requirements": ["Furnace"],
                "input_materials": [{"name": "Iron Ore", "quantity": 2}],
                "output_materials": [{"name": "Iron Ingot", "quantity": 1}],
                "confidence": 0.90
            }
        ],
        "analysis_type": "queue_analysis",
        "screenshots_processed": 1,
        "total_confidence": 0.925
    }


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "ai_analysis: marks tests as AI analysis tests")
    config.addinivalue_line("markers", "focus: marks tests that require BitCraft window focus")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "ai_analysis" in str(item.fspath):
            item.add_marker(pytest.mark.ai_analysis)


def pytest_runtest_setup(item):
    """Setup for individual test runs."""
    # Skip tests that require external dependencies if not available
    markers = [marker.name for marker in item.iter_markers()]
    
    if "ai_analysis" in markers:
        # Check if AI analysis modules are available
        try:
            from bitcrafty_extractor.ai_analysis.vision_client import VisionClient
        except ImportError:
            pytest.skip("AI analysis modules not available")
    
    if "focus" in markers:
        # Skip focus tests in CI or if BitCraft not available
        import os
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            pytest.skip("Focus tests skipped in CI environment")


@pytest.fixture(autouse=True)
def suppress_logging():
    """Suppress logging during tests unless explicitly needed."""
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger('bitcrafty_extractor').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
