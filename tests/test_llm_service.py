import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_service import (
    is_provider_available,
    get_provider_config,
    get_available_providers,
    PROVIDER_LOCAL,
    PROVIDER_OPENAI_COMPATIBLE,
    PROVIDER_ANTHROPIC,
)


class TestLLMServiceProviderAvailability(unittest.TestCase):
    """Tests for is_provider_available in llm_service module."""

    def setUp(self):
        """Set up test environment variables."""
        # Save original environment
        self.original_env = dict(os.environ)
        
        # Clear relevant environment variables
        for key in ["LOCAL_LLM_BASE_URL", "LOCAL_LLM_API_KEY", "LOCAL_LLM_MODEL",
                      "HOSTED_LLM_BASE_URL", "HOSTED_LLM_API_KEY", "HOSTED_LLM_MODEL",
                      "HOSTED_LLM_TIMEOUT", "HOSTED_LLM_MAX_TOKENS",
                      "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
                      "ANTHROPIC_TIMEOUT", "ANTHROPIC_MAX_TOKENS",
                      "DEFAULT_MODEL_PROVIDER"]:
            if key in os.environ:
                del os.environ[key]

    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('services.llm_service.requests.get')
    def test_is_provider_available_openai_compatible_configured_no_http_call(self, mock_get):
        """Test that is_provider_available returns True for openai_compatible when configured, without making HTTP calls."""
        # Configure environment for hosted OpenAI-compatible provider
        os.environ["HOSTED_LLM_BASE_URL"] = "https://router.huggingface.co/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-api-key"
        os.environ["HOSTED_LLM_MODEL"] = "openai/gpt-oss-120b"
        
        # Call the function
        result = is_provider_available("openai_compatible")
        
        # Assert it returns True (available)
        self.assertTrue(result)
        
        # Verify NO HTTP requests were made
        mock_get.assert_not_called()

    @patch('services.llm_service.requests.get')
    def test_is_provider_available_openai_compatible_not_configured(self, mock_get):
        """Test that openai_compatible provider is not available when not configured."""
        # Ensure no env vars are set
        for key in ["HOSTED_LLM_BASE_URL", "HOSTED_LLM_API_KEY", "HOSTED_LLM_MODEL"]:
            if key in os.environ:
                del os.environ[key]
        
        result = is_provider_available("openai_compatible")
        self.assertFalse(result)
        # No HTTP calls should be made
        self.assertFalse(mock_get.called)

    @patch('services.llm_service.requests.get')
    def test_is_provider_available_local_provider_health_check(self, mock_get):
        """Test that local provider still performs health checks."""
        os.environ["LOCAL_LLM_BASE_URL"] = "http://localhost:8080/v1"
        os.environ["LOCAL_LLM_API_KEY"] = "not-needed"
        
        # Mock successful health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = is_provider_available("local")
        self.assertTrue(result)
        # Should have made the health check call
        mock_get.assert_called()

    @patch('services.llm_service.requests.get')
    def test_is_provider_available_anthropic_configured(self, mock_get):
        """Test that Anthropic provider is available when API key is set."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
        
        result = is_provider_available("anthropic")
        self.assertTrue(result)
        # No HTTP calls should be made for Anthropic
        mock_get.assert_not_called()

    @patch('services.llm_service.requests.get')
    def test_is_provider_available_anthropic_not_configured(self, mock_get):
        """Test Anthropic provider not available when not configured."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        result = is_provider_available("anthropic")
        self.assertFalse(result)
        mock_get.assert_not_called()

    @patch('services.llm_service.requests.get')
    def test_is_provider_available_local_not_configured(self, mock_get):
        """Test local provider not available when server not running."""
        os.environ["LOCAL_LLM_BASE_URL"] = "http://localhost:8080/v1"
        os.environ["LOCAL_LLM_API_KEY"] = "not-needed"
        
        # Mock failed health check
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Should fail health check and then try /models
        mock_response2 = MagicMock()
        mock_response2.status_code = 500
        mock_get.side_effect = [mock_response, mock_response2]
        
        result = is_provider_available("local")
        self.assertFalse(result)
        # Should have made both health check and models calls
        self.assertEqual(mock_get.call_count, 2)


if __name__ == "__main__":
    unittest.main()