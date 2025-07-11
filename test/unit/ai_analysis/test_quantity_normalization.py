"""Test quantity normalization functionality in vision client."""

import pytest
from pathlib import Path
import sys

# Add src to path  
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from bitcrafty_extractor.ai_analysis.vision_client import VisionClient
    import structlog
    VISION_CLIENT_AVAILABLE = True
except ImportError:
    VISION_CLIENT_AVAILABLE = False


@pytest.mark.skipif(not VISION_CLIENT_AVAILABLE, reason="Vision client not available")
class TestQuantityNormalization:
    """Test quantity normalization functionality."""
    
    @pytest.fixture
    def vision_client(self):
        """Create a VisionClient instance for testing."""
        logger = structlog.get_logger(__name__)
        return VisionClient(logger)
    
    def test_normalize_quantity_integers(self, vision_client):
        """Test normalization of integer quantities."""
        assert vision_client._normalize_quantity(1) == 1
        assert vision_client._normalize_quantity(5) == 5
        assert vision_client._normalize_quantity(100) == 100
    
    def test_normalize_quantity_string_integers(self, vision_client):
        """Test normalization of string integer quantities."""
        assert vision_client._normalize_quantity("1") == 1
        assert vision_client._normalize_quantity("5") == 5
        assert vision_client._normalize_quantity(" 10 ") == 10
    
    def test_normalize_quantity_ranges(self, vision_client):
        """Test normalization of range quantities."""
        assert vision_client._normalize_quantity("1-3") == "1-3"
        assert vision_client._normalize_quantity("0-2") == "0-2"
        assert vision_client._normalize_quantity("10-20") == "10-20"
        assert vision_client._normalize_quantity(" 5-8 ") == "5-8"
    
    def test_normalize_quantity_variable_terms(self, vision_client):
        """Test normalization of variable/varied terms."""
        assert vision_client._normalize_quantity("variable") == "0-1"
        assert vision_client._normalize_quantity("varied") == "0-1"
        assert vision_client._normalize_quantity("random") == "0-1"
        assert vision_client._normalize_quantity("varies") == "0-1"
        assert vision_client._normalize_quantity("multiple") == "0-1"
        assert vision_client._normalize_quantity("VARIABLE") == "0-1"
        assert vision_client._normalize_quantity("Varied") == "0-1"
    
    def test_normalize_quantity_invalid_values(self, vision_client):
        """Test normalization of invalid quantities."""
        assert vision_client._normalize_quantity("invalid_text") == "0-1"
        assert vision_client._normalize_quantity("") == "0-1"
        assert vision_client._normalize_quantity(None) == "0-1"
        assert vision_client._normalize_quantity([]) == "0-1"
        assert vision_client._normalize_quantity({}) == "0-1"
    
    def test_post_process_response_data_crafts_found(self, vision_client):
        """Test post-processing of response data with crafts_found."""
        response_data = {
            "analysis_type": "queue_analysis",
            "crafts_found": [
                {
                    "name": "Test Craft",
                    "materials": [
                        {"item": "Material A", "qty": 1},
                        {"item": "Material B", "qty": "variable"}
                    ],
                    "outputs": [
                        {"item": "Output A", "qty": "varied"},
                        {"item": "Output B", "qty": "2-4"}
                    ]
                }
            ]
        }
        
        processed = vision_client._post_process_response_data(response_data)
        
        craft = processed["crafts_found"][0]
        assert craft["materials"][0]["qty"] == 1
        assert craft["materials"][1]["qty"] == "0-1"
        assert craft["outputs"][0]["qty"] == "0-1"
        assert craft["outputs"][1]["qty"] == "2-4"
    
    def test_post_process_response_data_single_craft(self, vision_client):
        """Test post-processing of response data with single craft format."""
        response_data = {
            "name": "Test Craft",
            "materials": [
                {"item": "Material A", "qty": "random"},
                {"item": "Material B", "qty": 3}
            ],
            "outputs": [
                {"item": "Output A", "qty": "multiple"}
            ]
        }
        
        processed = vision_client._post_process_response_data(response_data)
        
        assert processed["materials"][0]["qty"] == "0-1"
        assert processed["materials"][1]["qty"] == 3
        assert processed["outputs"][0]["qty"] == "0-1"
    
    def test_post_process_response_data_no_changes_needed(self, vision_client):
        """Test post-processing when no changes are needed."""
        response_data = {
            "analysis_type": "queue_analysis",
            "crafts_found": [
                {
                    "name": "Test Craft",
                    "materials": [
                        {"item": "Material A", "qty": 1}
                    ],
                    "outputs": [
                        {"item": "Output A", "qty": "1-3"}
                    ]
                }
            ]
        }
        
        processed = vision_client._post_process_response_data(response_data)
        
        # Should be unchanged
        craft = processed["crafts_found"][0]
        assert craft["materials"][0]["qty"] == 1
        assert craft["outputs"][0]["qty"] == "1-3"
    
    def test_post_process_response_data_missing_fields(self, vision_client):
        """Test post-processing with missing or malformed fields."""
        response_data = {
            "analysis_type": "queue_analysis",
            "crafts_found": [
                {
                    "name": "Test Craft",
                    # No materials or outputs
                },
                {
                    "name": "Another Craft",
                    "materials": "not_a_list",
                    "outputs": [
                        {"item": "Output A"}  # No qty field
                    ]
                }
            ]
        }
        
        # Should not crash
        processed = vision_client._post_process_response_data(response_data)
        assert "crafts_found" in processed
        assert len(processed["crafts_found"]) == 2
