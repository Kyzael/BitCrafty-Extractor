"""Unit tests for VisionClient AI analysis component.

Tests the actual VisionClient functionality including initialization,
configuration, image processing, and cost tracking based on the real implementation.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from src.bitcrafty_extractor.ai_analysis.vision_client import (
    VisionClient, AIProvider, AIResponse, ImageData
)


class TestVisionClientReal:
    """Test cases for actual VisionClient implementation."""

    @pytest.fixture
    def mock_logger(self):
        """Mock structured logger."""
        return Mock()

    @pytest.fixture 
    def mock_config_manager(self):
        """Mock configuration manager with extraction config."""
        config_manager = Mock()
        # Mock the actual config structure based on real implementation
        config_manager.config.extraction.primary_provider.value = 'openai'
        config_manager.config.extraction.fallback_provider.value = 'anthropic'
        config_manager.config.extraction.rate_limit_delay = 1.0
        config_manager.config.openai.api_key = "test_openai_key"
        config_manager.config.openai.enabled = True
        config_manager.config.openai.model = "gpt-4o"
        config_manager.config.anthropic.api_key = "test_anthropic_key"
        config_manager.config.anthropic.enabled = True
        config_manager.config.anthropic.model = "claude-3-5-sonnet-20241022"
        return config_manager

    @pytest.fixture
    def mock_config_manager_no_extraction(self):
        """Mock configuration manager without extraction config."""
        config_manager = Mock()
        config_manager.config.extraction = None
        return config_manager

    @pytest.fixture
    def vision_client(self, mock_logger, mock_config_manager):
        """Create VisionClient instance for testing."""
        return VisionClient(mock_logger, mock_config_manager)

    @pytest.fixture
    def basic_vision_client(self, mock_logger):
        """Create VisionClient without config manager."""
        return VisionClient(mock_logger)

    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        image_array = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        return ImageData(image_array=image_array)

    @pytest.mark.unit
    def test_init_with_config(self, mock_logger, mock_config_manager):
        """Test VisionClient initialization with config manager."""
        client = VisionClient(mock_logger, mock_config_manager)
        assert client.logger == mock_logger
        assert client.config_manager == mock_config_manager
        assert client.default_provider == AIProvider.OPENAI_GPT4V
        assert client.fallback_provider == AIProvider.ANTHROPIC_CLAUDE
        assert client.total_cost == 0.0
        assert client.request_count == 0

    @pytest.mark.unit
    def test_init_without_config(self, mock_logger):
        """Test VisionClient initialization without config manager."""
        client = VisionClient(mock_logger)
        assert client.logger == mock_logger
        assert client.config_manager is None
        assert client.default_provider == AIProvider.OPENAI_GPT4V
        assert client.fallback_provider == AIProvider.ANTHROPIC_CLAUDE

    @pytest.mark.unit
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI')
    def test_configure_openai(self, mock_openai_class, basic_vision_client):
        """Test OpenAI client configuration."""
        basic_vision_client.configure_openai("test_api_key", "gpt-4o")
        assert basic_vision_client.openai_client is not None
        assert basic_vision_client.openai_model == "gpt-4o"
        mock_openai_class.assert_called_once_with(api_key="test_api_key")

    @pytest.mark.unit
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.anthropic.Anthropic')
    def test_configure_anthropic(self, mock_anthropic_class, basic_vision_client):
        """Test Anthropic client configuration."""
        basic_vision_client.configure_anthropic("test_api_key", "claude-3-5-sonnet-20241022")
        assert basic_vision_client.anthropic_client is not None
        assert basic_vision_client.anthropic_model == "claude-3-5-sonnet-20241022"
        mock_anthropic_class.assert_called_once_with(api_key="test_api_key")

    @pytest.mark.unit
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.Image')
    def test_prepare_image(self, mock_pil, vision_client, sample_image_data):
        """Test image preparation for AI analysis."""
        # Mock PIL Image operations
        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_pil.fromarray.return_value = mock_image
        mock_image.resize.return_value = mock_image
        mock_image.save.return_value = None
        
        with patch('base64.b64encode') as mock_b64:
            mock_b64.return_value.decode.return_value = "encoded_image_data"
            
            result = vision_client._prepare_image(sample_image_data)
            
            assert result == "encoded_image_data"
            mock_pil.fromarray.assert_called_once()

    @pytest.mark.unit
    def test_estimate_cost(self, vision_client):
        """Test cost estimation for different providers."""
        openai_cost = vision_client._estimate_cost(AIProvider.OPENAI_GPT4V, 1000000)
        anthropic_cost = vision_client._estimate_cost(AIProvider.ANTHROPIC_CLAUDE, 1000000)
        
        assert isinstance(openai_cost, float)
        assert isinstance(anthropic_cost, float)
        assert openai_cost > 0
        assert anthropic_cost > 0

    @pytest.mark.unit
    def test_extract_json_from_response(self, vision_client):
        """Test JSON extraction from AI responses."""
        # Test direct JSON
        json_response = '{"test": "value"}'
        result = vision_client._extract_json_from_response(json_response)
        assert result == {"test": "value"}
        
        # Test markdown code block
        markdown_response = "```json\n{\"test\": \"value\"}\n```"
        result = vision_client._extract_json_from_response(markdown_response)
        assert result == {"test": "value"}
        
        # Test plain text fallback
        text_response = "This is just text"
        result = vision_client._extract_json_from_response(text_response)
        assert result == {"raw_text": "This is just text"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.asyncio.to_thread')
    async def test_analyze_with_openai(self, mock_to_thread, vision_client, sample_image_data):
        """Test OpenAI analysis."""
        # Mock the OpenAI client and response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"test": "response"}'
        
        vision_client.openai_client = Mock()
        mock_to_thread.return_value = mock_response
        
        with patch.object(vision_client, '_prepare_image', return_value="base64_image"):
            result = await vision_client._analyze_with_openai("test prompt", "base64_image")
            
            assert isinstance(result, AIResponse)
            assert result.provider == AIProvider.OPENAI_GPT4V
            assert result.success is True

    @pytest.mark.unit
    @pytest.mark.asyncio 
    async def test_analyze_image_no_clients(self, basic_vision_client, sample_image_data):
        """Test analyze_image when no clients are configured."""
        with pytest.raises(RuntimeError) as exc_info:
            await basic_vision_client.analyze_image(
                sample_image_data, 
                "test prompt"
            )
        
        assert "OpenAI client not configured" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_images_empty_list(self, vision_client):
        """Test analyze_images with empty image list."""
        result = await vision_client.analyze_images([], "test prompt")
        
        assert result.success is False
        assert "No images provided" in result.error_message

    @pytest.mark.unit
    def test_get_stats(self, vision_client):
        """Test getting usage statistics."""
        stats = vision_client.get_stats()
        
        assert "total_requests" in stats
        assert "total_cost" in stats
        assert "average_cost_per_request" in stats
        assert "configured_providers" in stats
        assert "default_provider" in stats
        assert "fallback_provider" in stats
        
        assert stats["total_requests"] == 0
        assert stats["total_cost"] == 0.0


# Parametrized tests for AI providers
@pytest.mark.unit
@pytest.mark.parametrize("provider_enum,expected_value", [
    (AIProvider.OPENAI_GPT4V, "openai_gpt4v"),
    (AIProvider.ANTHROPIC_CLAUDE, "anthropic_claude"),
])
def test_ai_provider_enum(provider_enum, expected_value):
    """Test AI provider enum values."""
    assert provider_enum.value == expected_value


@pytest.mark.unit
def test_ai_response_dataclass():
    """Test AIResponse dataclass creation."""
    response = AIResponse(
        success=True,
        data={"test": "data"},
        confidence=0.8,
        provider=AIProvider.OPENAI_GPT4V,
        cost_estimate=0.01,
        processing_time=1.5,
        raw_response="raw response"
    )
    
    assert response.success is True
    assert response.data == {"test": "data"}
    assert response.confidence == 0.8
    assert response.provider == AIProvider.OPENAI_GPT4V
    assert response.cost_estimate == 0.01
    assert response.processing_time == 1.5
    assert response.raw_response == "raw response"
    assert response.error_message is None


@pytest.mark.unit
def test_image_data_dataclass():
    """Test ImageData dataclass creation."""
    image_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    image_data = ImageData(
        image_array=image_array,
        format="JPEG",
        quality=90,
        max_size=512
    )
    
    assert np.array_equal(image_data.image_array, image_array)
    assert image_data.format == "JPEG"
    assert image_data.quality == 90
    assert image_data.max_size == 512


@pytest.fixture
def mock_config_manager_no_extraction():
    """Mock configuration manager without extraction config."""
    config_manager = Mock()
    config_manager.config.extraction = None
    return config_manager


@pytest.mark.unit
def test_vision_client_cost_tracking(mock_logger, mock_config_manager_no_extraction):
    """Test that cost tracking works correctly."""
    vision_client = VisionClient(mock_logger, mock_config_manager_no_extraction)
    initial_cost = vision_client.total_cost
    initial_requests = vision_client.request_count
    
    # Simulate adding cost
    vision_client.total_cost += 0.05
    vision_client.request_count += 1
    
    assert vision_client.total_cost == initial_cost + 0.05
    assert vision_client.request_count == initial_requests + 1
    
    stats = vision_client.get_stats()
    assert stats["total_cost"] == vision_client.total_cost
    assert stats["total_requests"] == vision_client.request_count
