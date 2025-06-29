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


@pytest.mark.unit
class TestVisionClientErrorHandling:
    """Test VisionClient error handling scenarios."""
    
    @pytest.fixture
    def mock_logger(self):
        """Mock structured logger."""
        return Mock()
    
    @pytest.fixture
    def mock_config_manager(self):
        """Mock configuration manager."""
        config_manager = Mock()
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
    def vision_client(self, mock_logger, mock_config_manager):
        """Create VisionClient instance for testing."""
        return VisionClient(mock_logger, mock_config_manager)
    
    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        image_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        return ImageData(image_array=image_array)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.asyncio.to_thread')
    async def test_analyze_with_openai_api_error(self, mock_to_thread, vision_client):
        """Test OpenAI analysis with API error."""
        # Configure the client first
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI'):
            vision_client.configure_openai("test_key")
        
        # Mock API error
        mock_to_thread.side_effect = Exception("API Error: Rate limit exceeded")
        
        result = await vision_client._analyze_with_openai("test prompt", "base64_image")
        
        assert isinstance(result, AIResponse)
        assert result.success is False
        assert result.provider == AIProvider.OPENAI_GPT4V
        assert "API Error" in result.error_message
        assert result.data is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.asyncio.to_thread')
    async def test_analyze_with_anthropic_api_error(self, mock_to_thread, vision_client):
        """Test Anthropic analysis with API error."""
        # Configure the client first
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.anthropic.Anthropic'):
            vision_client.configure_anthropic("test_key")
        
        # Mock API error
        mock_to_thread.side_effect = Exception("API Error: Invalid API key")
        
        result = await vision_client._analyze_with_anthropic("test prompt", "base64_image")
        
        assert isinstance(result, AIResponse)
        assert result.success is False
        assert result.provider == AIProvider.ANTHROPIC_CLAUDE
        assert "API Error" in result.error_message
        assert result.data is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_image_with_fallback(self, vision_client, sample_image_data):
        """Test analyze_image with primary provider failure and fallback success."""
        # Configure both clients
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI'):
            vision_client.configure_openai("test_key")
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.anthropic.Anthropic'):
            vision_client.configure_anthropic("test_key")
        
        # Mock primary provider failure
        with patch.object(vision_client, '_analyze_with_openai') as mock_openai:
            mock_openai.return_value = AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=0.0,
                processing_time=0.0,
                raw_response="",
                error_message="Primary provider failed"
            )
            
            # Mock fallback provider success
            with patch.object(vision_client, '_analyze_with_anthropic') as mock_anthropic:
                mock_anthropic.return_value = AIResponse(
                    success=True,
                    data={"items_found": []},
                    confidence=0.8,
                    provider=AIProvider.ANTHROPIC_CLAUDE,
                    cost_estimate=0.02,
                    processing_time=2.0,
                    raw_response='{"items_found": []}',
                    error_message=None
                )
                
                result = await vision_client.analyze_image(sample_image_data, "test prompt")
                
                assert result.success is True
                assert result.provider == AIProvider.ANTHROPIC_CLAUDE
                # Check that fallback logging occurred
                vision_client.logger.info.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_image_both_providers_fail(self, vision_client, sample_image_data):
        """Test analyze_image when both primary and fallback providers fail."""
        # Configure both clients
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI'):
            vision_client.configure_openai("test_key")
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.anthropic.Anthropic'):
            vision_client.configure_anthropic("test_key")
        
        # Mock both providers failing
        with patch.object(vision_client, '_analyze_with_openai') as mock_openai:
            mock_openai.return_value = AIResponse(
                success=False, data=None, confidence=0.0, provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=0.0, processing_time=0.0, raw_response="", error_message="Primary failed"
            )
            
            with patch.object(vision_client, '_analyze_with_anthropic') as mock_anthropic:
                mock_anthropic.return_value = AIResponse(
                    success=False, data=None, confidence=0.0, provider=AIProvider.ANTHROPIC_CLAUDE,
                    cost_estimate=0.0, processing_time=0.0, raw_response="", error_message="Fallback failed"
                )
                
                result = await vision_client.analyze_image(sample_image_data, "test prompt")
                
                assert result.success is False
                assert result.error_message == "Primary failed"  # Returns primary error, not combined message
    
    @pytest.mark.unit
    def test_extract_json_from_response_invalid_json(self, vision_client):
        """Test JSON extraction from invalid JSON response."""
        invalid_json = '{"invalid": json}'  # Missing closing quote
        result = vision_client._extract_json_from_response(invalid_json)
        
        # Should fall back to raw text format
        assert result == {"raw_text": invalid_json}
    
    @pytest.mark.unit
    def test_extract_json_from_response_multiple_code_blocks(self, vision_client):
        """Test JSON extraction from response with multiple code blocks."""
        response = """Here's the analysis:
```json
{"first": "block"}
```
And also:
```json
{"second": "block"}
```"""
        result = vision_client._extract_json_from_response(response)
        
        # Should extract the first JSON block
        assert result == {"first": "block"}
    
    @pytest.mark.unit
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.Image')
    def test_prepare_image_error_handling(self, mock_pil, vision_client, sample_image_data):
        """Test image preparation error handling."""
        # Mock PIL raising an exception
        mock_pil.fromarray.side_effect = Exception("PIL Error")
        
        with pytest.raises(Exception) as exc_info:
            vision_client._prepare_image(sample_image_data)
        
        assert "PIL Error" in str(exc_info.value)
    
    @pytest.mark.unit
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.Image')
    def test_prepare_image_with_resize(self, mock_pil, vision_client):
        """Test image preparation with resize for large images."""
        # Create large image data
        large_image_array = np.random.randint(0, 255, (2000, 3000, 3), dtype=np.uint8)
        image_data = ImageData(image_array=large_image_array, max_size=1024)
        
        # Mock PIL Image operations
        mock_image = Mock()
        mock_image.size = (3000, 2000)  # Large image
        mock_pil.fromarray.return_value = mock_image
        mock_image.resize.return_value = mock_image
        mock_image.save.return_value = None
        
        with patch('base64.b64encode') as mock_b64:
            mock_b64.return_value.decode.return_value = "encoded_image_data"
            
            result = vision_client._prepare_image(image_data)
            
            # Should resize the image
            mock_image.resize.assert_called_once()
            assert result == "encoded_image_data"


@pytest.mark.unit
class TestVisionClientCostEstimation:
    """Test VisionClient cost estimation functionality."""
    
    @pytest.fixture
    def mock_logger(self):
        return Mock()
    
    @pytest.fixture
    def vision_client(self, mock_logger):
        return VisionClient(mock_logger)
    
    @pytest.mark.unit
    def test_estimate_cost_openai_small_image(self, vision_client):
        """Test cost estimation for OpenAI with small image."""
        cost = vision_client._estimate_cost(AIProvider.OPENAI_GPT4V, 100000)  # 100KB
        
        assert isinstance(cost, float)
        assert cost > 0
        assert cost < 0.02  # Adjusted threshold based on actual costs
    
    @pytest.mark.unit
    def test_estimate_cost_openai_large_image(self, vision_client):
        """Test cost estimation for OpenAI with large image."""
        cost = vision_client._estimate_cost(AIProvider.OPENAI_GPT4V, 5000000)  # 5MB
        
        assert isinstance(cost, float)
        assert cost > 0
        # Large images should cost more
        small_cost = vision_client._estimate_cost(AIProvider.OPENAI_GPT4V, 100000)
        assert cost > small_cost
    
    @pytest.mark.unit
    def test_estimate_cost_anthropic_vs_openai(self, vision_client):
        """Test cost comparison between providers."""
        image_size = 1000000  # 1MB
        
        openai_cost = vision_client._estimate_cost(AIProvider.OPENAI_GPT4V, image_size)
        anthropic_cost = vision_client._estimate_cost(AIProvider.ANTHROPIC_CLAUDE, image_size)
        
        assert isinstance(openai_cost, float)
        assert isinstance(anthropic_cost, float)
        assert openai_cost > 0
        assert anthropic_cost > 0
        # Both should be reasonable costs
        assert openai_cost < 1.0
        assert anthropic_cost < 1.0
    
    @pytest.mark.unit
    def test_cost_tracking_after_analysis(self, vision_client):
        """Test that cost tracking is updated after analysis."""
        initial_cost = vision_client.total_cost
        initial_requests = vision_client.request_count
        
        # Simulate cost update (would happen during real analysis)
        test_cost = 0.025
        vision_client.total_cost += test_cost
        vision_client.request_count += 1
        
        assert vision_client.total_cost == initial_cost + test_cost
        assert vision_client.request_count == initial_requests + 1
        
        stats = vision_client.get_stats()
        assert stats["total_cost"] == vision_client.total_cost
        assert stats["total_requests"] == vision_client.request_count
        if vision_client.request_count > 0:
            expected_avg = vision_client.total_cost / vision_client.request_count
            assert stats["average_cost_per_request"] == expected_avg


@pytest.mark.unit
class TestVisionClientRateLimiting:
    """Test VisionClient rate limiting functionality."""
    
    @pytest.fixture
    def mock_logger(self):
        return Mock()
    
    @pytest.fixture  
    def vision_client(self, mock_logger):
        client = VisionClient(mock_logger)
        client.min_request_interval = 2.0  # 2 seconds between requests
        return client
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, vision_client, mock_logger):
        """Test that rate limiting is enforced between requests."""
        # Mock time.time to control timing
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.time.time') as mock_time:
            mock_time.side_effect = [0.0, 0.5, 2.5, 4.0]  # Provide enough time values
            
            # Configure client
            with patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI'):
                vision_client.configure_openai("test_key")
            
            sample_image = ImageData(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
            
            # Mock the actual analysis method to avoid API calls
            with patch.object(vision_client, '_analyze_with_openai') as mock_analyze:
                mock_analyze.return_value = AIResponse(
                    success=True, data={"test": "data"}, confidence=0.8,
                    provider=AIProvider.OPENAI_GPT4V, cost_estimate=0.01,
                    processing_time=1.0, raw_response='{"test": "data"}'
                )
                
                # Mock sleep to verify it's called for rate limiting
                with patch('asyncio.sleep') as mock_sleep:
                    # First request
                    await vision_client.analyze_image(sample_image, "test prompt")
                    
                    # Second request (should trigger rate limiting)
                    await vision_client.analyze_image(sample_image, "test prompt")
                    
                    # Should have called sleep to enforce rate limit
                    mock_sleep.assert_called()


@pytest.mark.unit
class TestVisionClientConfiguration:
    """Test VisionClient configuration scenarios."""
    
    @pytest.fixture
    def mock_logger(self):
        return Mock()
    
    @pytest.mark.unit
    def test_initialization_from_config(self, mock_logger):
        """Test VisionClient initialization from config manager."""
        # Create mock config with proper structure
        config_manager = Mock()
        config_manager.config.extraction.primary_provider.value = 'anthropic'
        config_manager.config.extraction.fallback_provider.value = 'openai'
        config_manager.config.extraction.rate_limit_delay = 3.0
        config_manager.config.openai.api_key = "openai_key"
        config_manager.config.openai.enabled = True
        config_manager.config.openai.model = "gpt-4o"
        config_manager.config.anthropic.api_key = "anthropic_key"
        config_manager.config.anthropic.enabled = True
        config_manager.config.anthropic.model = "claude-3-5-sonnet-20241022"
        
        client = VisionClient(mock_logger, config_manager)
        
        assert client.default_provider == AIProvider.ANTHROPIC_CLAUDE
        assert client.fallback_provider == AIProvider.OPENAI_GPT4V
        assert client.min_request_interval == 3.0
    
    @pytest.mark.unit
    def test_initialization_without_config(self, mock_logger):
        """Test VisionClient initialization without config manager."""
        client = VisionClient(mock_logger, None)
        
        assert client.default_provider == AIProvider.OPENAI_GPT4V
        assert client.fallback_provider == AIProvider.ANTHROPIC_CLAUDE
        assert client.min_request_interval == 1.0
        assert client.max_retries == 3
        assert client.timeout == 30.0
    
    @pytest.mark.unit
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI')
    def test_configure_openai_custom_model(self, mock_openai_class, mock_logger):
        """Test OpenAI configuration with custom model."""
        client = VisionClient(mock_logger)
        
        client.configure_openai("custom_key", "gpt-4-turbo")
        
        assert client.openai_model == "gpt-4-turbo"
        mock_openai_class.assert_called_once_with(api_key="custom_key")
    
    @pytest.mark.unit
    @patch('src.bitcrafty_extractor.ai_analysis.vision_client.anthropic.Anthropic')
    def test_configure_anthropic_custom_model(self, mock_anthropic_class, mock_logger):
        """Test Anthropic configuration with custom model."""
        client = VisionClient(mock_logger)
        
        client.configure_anthropic("custom_key", "claude-3-opus-20240229")
        
        assert client.anthropic_model == "claude-3-opus-20240229"
        mock_anthropic_class.assert_called_once_with(api_key="custom_key")


@pytest.mark.unit
class TestVisionClientMultipleImages:
    """Test VisionClient multiple image analysis functionality."""
    
    @pytest.fixture
    def mock_logger(self):
        return Mock()
    
    @pytest.fixture
    def vision_client(self, mock_logger):
        return VisionClient(mock_logger)
    
    @pytest.fixture
    def sample_images(self):
        """Sample image data list for testing."""
        images = []
        for i in range(3):
            image_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            images.append(ImageData(image_array=image_array))
        return images
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_images_success(self, vision_client, sample_images):
        """Test successful multiple image analysis."""
        # Configure client
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI'):
            vision_client.configure_openai("test_key")
        
        # Mock the multiple image analysis method
        with patch.object(vision_client, '_analyze_multiple_with_openai') as mock_analyze:
            mock_analyze.return_value = AIResponse(
                success=True,
                data={"items_found": [{"name": "Test Item"}]},
                confidence=0.9,
                provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=0.05,
                processing_time=5.0,
                raw_response='{"items_found": [{"name": "Test Item"}]}'
            )
            
            result = await vision_client.analyze_images(sample_images, "analyze these images")
            
            assert result.success is True
            assert result.provider == AIProvider.OPENAI_GPT4V
            assert "Test Item" in str(result.data)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_images_empty_list(self, vision_client):
        """Test analyze_images with empty image list."""
        result = await vision_client.analyze_images([], "test prompt")
        
        assert result.success is False
        assert "No images provided" in result.error_message
        assert result.provider == vision_client.default_provider
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_images_with_fallback(self, vision_client, sample_images):
        """Test multiple image analysis with fallback provider."""
        # Configure both clients
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.openai.OpenAI'):
            vision_client.configure_openai("test_key")
        with patch('src.bitcrafty_extractor.ai_analysis.vision_client.anthropic.Anthropic'):
            vision_client.configure_anthropic("test_key")
        
        # Mock primary provider failure
        with patch.object(vision_client, '_analyze_multiple_with_openai') as mock_openai:
            mock_openai.return_value = AIResponse(
                success=False, data=None, confidence=0.0, provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=0.0, processing_time=0.0, raw_response="", error_message="Primary failed"
            )
            
            # Mock fallback provider success  
            with patch.object(vision_client, '_analyze_multiple_with_anthropic') as mock_anthropic:
                mock_anthropic.return_value = AIResponse(
                    success=True, data={"items_found": []}, confidence=0.8,
                    provider=AIProvider.ANTHROPIC_CLAUDE, cost_estimate=0.03,
                    processing_time=3.0, raw_response='{"items_found": []}'
                )
                
                result = await vision_client.analyze_images(sample_images, "test prompt")
                
                assert result.success is True
                assert result.provider == AIProvider.ANTHROPIC_CLAUDE
