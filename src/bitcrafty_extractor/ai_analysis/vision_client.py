"""AI Vision client for analyzing game interface screenshots.

This module handles communication with AI vision models (OpenAI GPT-4 Vision, 
Anthropic Claude) to extract structured game data from screenshots.
"""

import base64
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import asyncio
import structlog
from dataclasses import dataclass
from enum import Enum
from io import BytesIO

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from PIL import Image
    import numpy as np
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False


class AIProvider(Enum):
    """Available AI vision providers."""
    OPENAI_GPT4V = "openai_gpt4v"
    ANTHROPIC_CLAUDE = "anthropic_claude"


@dataclass
class AIResponse:
    """Response from AI vision analysis."""
    success: bool
    data: Optional[Dict[str, Any]]
    confidence: float
    provider: AIProvider
    cost_estimate: float
    processing_time: float
    raw_response: str
    error_message: Optional[str] = None


@dataclass
class ImageData:
    """Container for image data to be analyzed."""
    image_array: np.ndarray
    format: str = "PNG"
    quality: int = 85
    max_size: int = 1024  # Max width/height for cost optimization


class VisionClient:
    """AI vision client for game interface analysis."""
    
    def __init__(self, logger: structlog.BoundLogger, config_manager=None):
        """Initialize the vision client.
        
        Args:
            logger: Structured logger for operation tracking
            config_manager: Configuration manager for API keys and settings
        """
        self.logger = logger
        self.config_manager = config_manager
        self.openai_client = None
        self.anthropic_client = None
        
        # Cost tracking
        self.total_cost = 0.0
        self.request_count = 0
        
        # Rate limiting
        self.last_request_time = 0.0
        self.min_request_interval = 1.0  # seconds
        
        # Configuration - use config_manager if available
        if config_manager and config_manager.config.extraction:
            self.default_provider = (AIProvider.OPENAI_GPT4V if config_manager.config.extraction.primary_provider.value == 'openai' 
                                    else AIProvider.ANTHROPIC_CLAUDE)
            self.fallback_provider = (AIProvider.OPENAI_GPT4V if config_manager.config.extraction.fallback_provider.value == 'openai' 
                                     else AIProvider.ANTHROPIC_CLAUDE)
            self.min_request_interval = config_manager.config.extraction.rate_limit_delay
        else:
            self.default_provider = AIProvider.OPENAI_GPT4V
            self.fallback_provider = AIProvider.ANTHROPIC_CLAUDE
        self.max_retries = 3
        self.timeout = 30.0
        
        self.logger.info("Vision client initialized")

        # Initialize clients from config if available
        if config_manager:
            self._initialize_from_config()

    def _initialize_from_config(self):
        """Initialize AI clients from configuration manager."""
        if not self.config_manager:
            return
            
        # Configure OpenAI if available
        openai_config = self.config_manager.config.openai
        if openai_config and openai_config.enabled and openai_config.api_key:
            try:
                self.configure_openai(openai_config.api_key, openai_config.model)
            except Exception as e:
                self.logger.warning("Failed to configure OpenAI", error=str(e))
        
        # Configure Anthropic if available  
        anthropic_config = self.config_manager.config.anthropic
        if anthropic_config and anthropic_config.enabled and anthropic_config.api_key:
            try:
                self.configure_anthropic(anthropic_config.api_key, anthropic_config.model)
            except Exception as e:
                self.logger.warning("Failed to configure Anthropic", error=str(e))

    def configure_openai(self, api_key: str, model: str = "gpt-4o"):
        """Configure OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model name to use (gpt-4o, gpt-4o-mini for vision)
        """
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI library not available. Install openai package.")
        
        self.openai_client = openai.OpenAI(api_key=api_key)
        self.openai_model = model
        
        self.logger.info("OpenAI client configured", model=model)

    def configure_anthropic(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """Configure Anthropic client.
        
        Args:
            api_key: Anthropic API key
            model: Model name to use
        """
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic library not available. Install anthropic package.")
        
        self.anthropic_client = anthropic.Anthropic(api_key=api_key)
        self.anthropic_model = model
        
        self.logger.info("Anthropic client configured", model=model)

    def _prepare_image(self, image_data: ImageData) -> str:
        """Prepare image for AI analysis by compressing and encoding.
        
        Args:
            image_data: Image data container
            
        Returns:
            Base64 encoded image string
        """
        try:
            # Convert numpy array to PIL Image
            if len(image_data.image_array.shape) == 3:
                # BGR to RGB conversion for OpenCV images
                rgb_array = image_data.image_array[:, :, ::-1]
            else:
                rgb_array = image_data.image_array
            
            pil_image = Image.fromarray(rgb_array)
            
            # Resize for cost optimization while maintaining aspect ratio
            width, height = pil_image.size
            if width > image_data.max_size or height > image_data.max_size:
                ratio = min(image_data.max_size / width, image_data.max_size / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                self.logger.debug("Image resized for optimization",
                                original_size=f"{width}x{height}",
                                new_size=f"{new_width}x{new_height}")
            
            # Convert to bytes
            buffer = BytesIO()
            pil_image.save(buffer, format=image_data.format, quality=image_data.quality)
            image_bytes = buffer.getvalue()
            
            # Encode to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            self.logger.debug("Image prepared for AI analysis",
                            format=image_data.format,
                            size_kb=len(image_bytes) // 1024)
            
            return base64_image
            
        except Exception as e:
            self.logger.error("Image preparation failed", error=str(e))
            raise

    def _estimate_cost(self, provider: AIProvider, image_size_bytes: int) -> float:
        """Estimate cost for AI analysis request.
        
        Args:
            provider: AI provider being used
            image_size_bytes: Size of image in bytes
            
        Returns:
            Estimated cost in USD
        """
        if provider == AIProvider.OPENAI_GPT4V:
            # GPT-4 Vision pricing (approximate)
            base_cost = 0.01  # Base cost per request
            size_cost = (image_size_bytes / 1000000) * 0.005  # Per MB
            return base_cost + size_cost
        elif provider == AIProvider.ANTHROPIC_CLAUDE:
            # Claude Vision pricing (approximate)
            base_cost = 0.008  # Base cost per request
            size_cost = (image_size_bytes / 1000000) * 0.004  # Per MB
            return base_cost + size_cost
        
        return 0.01  # Default estimate

    def _extract_json_from_response(self, raw_response: str) -> Dict[str, Any]:
        """Extract JSON data from AI response, handling markdown code blocks.
        
        Args:
            raw_response: Raw response text from AI
            
        Returns:
            Parsed JSON data or fallback structure
        """
        # First try direct JSON parsing
        try:
            data = json.loads(raw_response)
            return self._post_process_response_data(data)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        import re
        
        # Look for ```json ... ``` or ``` ... ``` blocks
        json_patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```'
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, raw_response, re.DOTALL)
            if match:
                try:
                    json_text = match.group(1).strip()
                    data = json.loads(json_text)
                    return self._post_process_response_data(data)
                except json.JSONDecodeError:
                    continue
        
        # If no JSON found, return as raw text
        return {"raw_text": raw_response}

    def _post_process_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process AI response data to clean up quantity formats.
        
        Args:
            data: Parsed JSON data from AI response
            
        Returns:
            Cleaned data with proper quantity formatting
        """
        # Process crafts_found array if it exists
        if 'crafts_found' in data and isinstance(data['crafts_found'], list):
            for craft in data['crafts_found']:
                if 'outputs' in craft and isinstance(craft['outputs'], list):
                    for output in craft['outputs']:
                        if 'qty' in output:
                            output['qty'] = self._normalize_quantity(output['qty'])
                
                if 'materials' in craft and isinstance(craft['materials'], list):
                    for material in craft['materials']:
                        if 'qty' in material:
                            material['qty'] = self._normalize_quantity(material['qty'])
        
        # Process single craft format
        if 'outputs' in data and isinstance(data['outputs'], list):
            for output in data['outputs']:
                if 'qty' in output:
                    output['qty'] = self._normalize_quantity(output['qty'])
        
        if 'materials' in data and isinstance(data['materials'], list):
            for material in data['materials']:
                if 'qty' in material:
                    material['qty'] = self._normalize_quantity(material['qty'])
        
        return data

    def _normalize_quantity(self, qty: Any) -> Union[int, str]:
        """Normalize quantity values to proper format.
        
        Args:
            qty: Quantity value (int, str, or other)
            
        Returns:
            Normalized quantity (int for fixed, str for ranges)
        """
        if isinstance(qty, int):
            return qty
        
        if isinstance(qty, str):
            qty_lower = qty.lower().strip()
            
            # Convert generic terms to default range
            if qty_lower in ['variable', 'varied', 'random', 'varies', 'multiple']:
                self.logger.info("Converting generic quantity term to default range", 
                               original=qty, normalized="0-1")
                return "0-1"
            
            # Check if it's already a proper range format
            range_match = re.match(r'^(\d+)-(\d+)$', qty.strip())
            if range_match:
                return qty.strip()
            
            # Try to parse as int
            try:
                return int(qty)
            except ValueError:
                # If we can't parse it, default to "0-1" 
                self.logger.warning("Could not parse quantity, defaulting to range", 
                                  original=qty, normalized="0-1")
                return "0-1"
        
        # For any other type, try to convert to int or default to "0-1"
        try:
            return int(qty)
        except (ValueError, TypeError):
            self.logger.warning("Unknown quantity type, defaulting to range", 
                              original=qty, normalized="0-1")
            return "0-1"

    async def _analyze_with_openai(self, prompt: str, image_base64: str) -> AIResponse:
        """Analyze image using OpenAI GPT-4 Vision.
        
        Args:
            prompt: Text prompt for analysis
            image_base64: Base64 encoded image
            
        Returns:
            AI response object
        """
        if not self.openai_client:
            raise RuntimeError("OpenAI client not configured")
        
        start_time = time.time()
        
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model=self.openai_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.1  # Low temperature for consistent extraction
                ),
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            raw_response = response.choices[0].message.content
            
            # Try to parse JSON response
            data = self._extract_json_from_response(raw_response)
            success = True
            confidence = data.get('confidence', 0.8) if 'raw_text' not in data else 0.6
            
            # Estimate cost
            cost_estimate = self._estimate_cost(AIProvider.OPENAI_GPT4V, len(image_base64))
            self.total_cost += cost_estimate
            self.request_count += 1
            
            self.logger.info("OpenAI analysis completed",
                           processing_time=processing_time,
                           cost_estimate=cost_estimate,
                           confidence=confidence)
            
            return AIResponse(
                success=success,
                data=data,
                confidence=confidence,
                provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=cost_estimate,
                processing_time=processing_time,
                raw_response=raw_response
            )
            
        except asyncio.TimeoutError:
            self.logger.error("OpenAI request timed out")
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=0.0,
                processing_time=time.time() - start_time,
                raw_response="",
                error_message="Request timed out"
            )
            
        except Exception as e:
            self.logger.error("OpenAI analysis failed", error=str(e))
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=0.0,
                processing_time=time.time() - start_time,
                raw_response="",
                error_message=str(e)
            )

    async def _analyze_with_anthropic(self, prompt: str, image_base64: str) -> AIResponse:
        """Analyze image using Anthropic Claude.
        
        Args:
            prompt: Text prompt for analysis
            image_base64: Base64 encoded image
            
        Returns:
            AI response object
        """
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not configured")
        
        start_time = time.time()
        
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model=self.anthropic_model,
                    max_tokens=1000,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_base64
                                    }
                                },
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ]
                ),
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            raw_response = response.content[0].text
            
            # Try to parse JSON response
            data = self._extract_json_from_response(raw_response)
            success = True
            confidence = data.get('confidence', 0.8) if 'raw_text' not in data else 0.6
            
            # Estimate cost
            cost_estimate = self._estimate_cost(AIProvider.ANTHROPIC_CLAUDE, len(image_base64))
            self.total_cost += cost_estimate
            self.request_count += 1
            
            self.logger.info("Anthropic analysis completed",
                           processing_time=processing_time,
                           cost_estimate=cost_estimate,
                           confidence=confidence)
            
            return AIResponse(
                success=success,
                data=data,
                confidence=confidence,
                provider=AIProvider.ANTHROPIC_CLAUDE,
                cost_estimate=cost_estimate,
                processing_time=processing_time,
                raw_response=raw_response
            )
            
        except Exception as e:
            self.logger.error("Anthropic analysis failed", error=str(e))
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=AIProvider.ANTHROPIC_CLAUDE,
                cost_estimate=0.0,
                processing_time=time.time() - start_time,
                raw_response="",
                error_message=str(e)
            )

    async def _analyze_multiple_with_openai(self, prompt: str, images_base64: List[str]) -> AIResponse:
        """Analyze multiple images using OpenAI GPT-4 Vision.
        
        Args:
            prompt: Text prompt for analysis
            images_base64: List of base64 encoded images
            
        Returns:
            AI response object
        """
        if not self.openai_client:
            raise RuntimeError("OpenAI client not configured")
        
        start_time = time.time()
        
        try:
            # Prepare content with multiple images
            content = []
            for i, image_base64 in enumerate(images_base64):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}",
                        "detail": "high"
                    }
                })
            
            # Add the text prompt at the end
            content.append({
                "type": "text",
                "text": f"{prompt}\n\nPlease analyze all {len(images_base64)} images together and provide a comprehensive extraction of items and crafts found across all screenshots."
            })
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model=self.openai_model,
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.1
                ),
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            raw_response = response.choices[0].message.content
            
            # Try to parse JSON response
            data = self._extract_json_from_response(raw_response)
            success = True
            confidence = data.get('confidence', 0.8) if 'raw_text' not in data else 0.6
            
            # Estimate cost for multiple images
            total_image_size = sum(len(img) for img in images_base64)
            cost_estimate = self._estimate_cost(AIProvider.OPENAI_GPT4V, total_image_size) * len(images_base64)
            self.total_cost += cost_estimate
            self.request_count += 1
            
            self.logger.info("OpenAI multi-image analysis completed",
                           image_count=len(images_base64),
                           processing_time=processing_time,
                           cost_estimate=cost_estimate,
                           confidence=confidence)
            
            return AIResponse(
                success=success,
                data=data,
                confidence=confidence,
                provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=cost_estimate,
                processing_time=processing_time,
                raw_response=raw_response
            )
            
        except Exception as e:
            self.logger.error("OpenAI multi-image analysis failed", error=str(e))
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=AIProvider.OPENAI_GPT4V,
                cost_estimate=0.0,
                processing_time=time.time() - start_time,
                raw_response="",
                error_message=str(e)
            )

    async def _analyze_multiple_with_anthropic(self, prompt: str, images_base64: List[str]) -> AIResponse:
        """Analyze multiple images using Anthropic Claude.
        
        Args:
            prompt: Text prompt for analysis
            images_base64: List of base64 encoded images
            
        Returns:
            AI response object
        """
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not configured")
        
        start_time = time.time()
        
        try:
            # Prepare content with multiple images
            content = []
            for i, image_base64 in enumerate(images_base64):
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_base64
                    }
                })
            
            # Add the text prompt at the end
            content.append({
                "type": "text", 
                "text": f"{prompt}\n\nPlease analyze all {len(images_base64)} images together and provide a comprehensive extraction of items and crafts found across all screenshots."
            })
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model=self.anthropic_model,
                    max_tokens=2000,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ]
                ),
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            raw_response = response.content[0].text
            
            # Try to parse JSON response
            data = self._extract_json_from_response(raw_response)
            success = True
            confidence = data.get('confidence', 0.8) if 'raw_text' not in data else 0.6
            
            # Estimate cost for multiple images
            total_image_size = sum(len(img) for img in images_base64)
            cost_estimate = self._estimate_cost(AIProvider.ANTHROPIC_CLAUDE, total_image_size) * len(images_base64)
            self.total_cost += cost_estimate
            self.request_count += 1
            
            self.logger.info("Anthropic multi-image analysis completed",
                           image_count=len(images_base64),
                           processing_time=processing_time,
                           cost_estimate=cost_estimate,
                           confidence=confidence)
            
            return AIResponse(
                success=success,
                data=data,
                confidence=confidence,
                provider=AIProvider.ANTHROPIC_CLAUDE,
                cost_estimate=cost_estimate,
                processing_time=processing_time,
                raw_response=raw_response
            )
            
        except Exception as e:
            self.logger.error("Anthropic multi-image analysis failed", error=str(e))
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=AIProvider.ANTHROPIC_CLAUDE,
                cost_estimate=0.0,
                processing_time=time.time() - start_time,
                raw_response="",
                error_message=str(e)
            )

    async def analyze_image(self, 
                          image_data: ImageData, 
                          prompt: str,
                          provider: Optional[AIProvider] = None,
                          use_fallback: bool = True) -> AIResponse:
        """Analyze an image using AI vision models.
        
        Args:
            image_data: Image data to analyze
            prompt: Text prompt describing what to extract
            provider: AI provider to use (defaults to configured default)
            use_fallback: Whether to try fallback provider on failure
            
        Returns:
            AI response with extracted data
        """
        if provider is None:
            provider = self.default_provider
        
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - (current_time - self.last_request_time))
        
        self.last_request_time = time.time()
        
        # Prepare image
        try:
            image_base64 = self._prepare_image(image_data)
        except Exception as e:
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=provider,
                cost_estimate=0.0,
                processing_time=0.0,
                raw_response="",
                error_message=f"Image preparation failed: {e}"
            )
        
        # Try primary provider
        if provider == AIProvider.OPENAI_GPT4V:
            response = await self._analyze_with_openai(prompt, image_base64)
        elif provider == AIProvider.ANTHROPIC_CLAUDE:
            response = await self._analyze_with_anthropic(prompt, image_base64)
        else:
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=provider,
                cost_estimate=0.0,
                processing_time=0.0,
                raw_response="",
                error_message=f"Unknown provider: {provider}"
            )
        
        # Try fallback provider if primary failed
        if not response.success and use_fallback and self.fallback_provider != provider:
            self.logger.info("Trying fallback provider", 
                           primary=provider.value,
                           fallback=self.fallback_provider.value)
            
            fallback_response = await self.analyze_image(
                image_data, prompt, self.fallback_provider, use_fallback=False
            )
            
            if fallback_response.success:
                return fallback_response
        
        return response

    async def analyze_images(self, 
                           image_data_list: List[ImageData], 
                           prompt: str,
                           provider: Optional[AIProvider] = None,
                           use_fallback: bool = True) -> AIResponse:
        """Analyze multiple images using AI vision models for queue analysis.
        
        Args:
            image_data_list: List of image data to analyze together
            prompt: Text prompt describing what to extract
            provider: AI provider to use (defaults to configured default)
            use_fallback: Whether to try fallback provider on failure
            
        Returns:
            AI response with extracted data from all images
        """
        if not image_data_list:
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=provider or self.default_provider,
                cost_estimate=0.0,
                processing_time=0.0,
                raw_response="",
                error_message="No images provided for analysis"
            )
        
        if provider is None:
            provider = self.default_provider
        
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - (current_time - self.last_request_time))
        
        self.last_request_time = time.time()
        
        # Prepare all images
        try:
            images_base64 = []
            for i, image_data in enumerate(image_data_list):
                try:
                    image_base64 = self._prepare_image(image_data)
                    images_base64.append(image_base64)
                except Exception as e:
                    self.logger.warning(f"Failed to prepare image {i+1}", error=str(e))
                    continue
            
            if not images_base64:
                return AIResponse(
                    success=False,
                    data=None,
                    confidence=0.0,
                    provider=provider,
                    cost_estimate=0.0,
                    processing_time=0.0,
                    raw_response="",
                    error_message="No images could be prepared for analysis"
                )
                
        except Exception as e:
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=provider,
                cost_estimate=0.0,
                processing_time=0.0,
                raw_response="",
                error_message=f"Image preparation failed: {e}"
            )
        
        # Try primary provider with multiple images
        if provider == AIProvider.OPENAI_GPT4V:
            response = await self._analyze_multiple_with_openai(prompt, images_base64)
        elif provider == AIProvider.ANTHROPIC_CLAUDE:
            response = await self._analyze_multiple_with_anthropic(prompt, images_base64)
        else:
            return AIResponse(
                success=False,
                data=None,
                confidence=0.0,
                provider=provider,
                cost_estimate=0.0,
                processing_time=0.0,
                raw_response="",
                error_message=f"Unknown provider: {provider}"
            )
        
        # Try fallback provider if primary failed
        if not response.success and use_fallback and self.fallback_provider != provider:
            self.logger.info("Trying fallback provider for multiple images", 
                           primary=provider.value,
                           fallback=self.fallback_provider.value)
            
            fallback_response = await self.analyze_images(
                image_data_list, prompt, self.fallback_provider, use_fallback=False
            )
            
            if fallback_response.success:
                return fallback_response
        
        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics.
        
        Returns:
            Dictionary with usage stats
        """
        return {
            "total_requests": self.request_count,
            "total_cost": round(self.total_cost, 4),
            "average_cost_per_request": round(self.total_cost / max(self.request_count, 1), 4),
            "configured_providers": {
                "openai": self.openai_client is not None,
                "anthropic": self.anthropic_client is not None
            },
            "default_provider": self.default_provider.value,
            "fallback_provider": self.fallback_provider.value
        }
