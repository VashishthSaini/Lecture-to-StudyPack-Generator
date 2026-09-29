import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.model_selection import (
    is_provider_available,
    get_provider_config,
    get_available_providers,
    select_model,
    get_provider_config,
    get_provider_status,
    PROVIDER_LOCAL,
    PROVIDER_OPENAI_COMPATIBLE,
    PROVIDER_ANTHROPIC,
)


class TestModelSelection(unittest.TestCase):
    """Tests for model_selection module."""

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

    def test_get_provider_config_local(self):
        """Test get_provider_config for local provider."""
        config = get_provider_config(PROVIDER_LOCAL)
        self.assertEqual(config["base_url"], "")
        self.assertEqual(config["api_key"], "not-needed")
        self.assertEqual(config["model"], "qwen3-4b-q4_k_m")
        self.assertTrue(config["is_configured"])

    def test_get_provider_config_openai_compatible(self):
        """Test get_provider_config for openai_compatible provider."""
        os.environ["HOSTED_LLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-key"
        os.environ["HOSTED_LLM_MODEL"] = "test-model"
        
        config = get_provider_config(PROVIDER_OPENAI_COMPATIBLE)
        self.assertEqual(config["base_url"], "https://api.example.com/v1")
        self.assertEqual(config["api_key"], "test-key")
        self.assertEqual(config["model"], "test-model")
        self.assertTrue(config["is_configured"])

    def test_get_provider_config_openai_compatible_not_configured(self):
        """Test get_provider_config for openai_compatible without config."""
        # Ensure no env vars set
        for key in ["HOSTED_LLM_BASE_URL", "HOSTED_LLM_API_KEY", "HOSTED_LLM_MODEL"]:
            if key in os.environ:
                del os.environ[key]
        
        config = get_provider_config(PROVIDER_OPENAI_COMPATIBLE)
        self.assertFalse(config["is_configured"])

    def test_get_provider_config_anthropic(self):
        """Test get_provider_config for anthropic provider."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
        os.environ["ANTHROPIC_MODEL"] = "claude-3-haiku-20240307"
        
        config = get_provider_config(PROVIDER_ANTHROPIC)
        self.assertEqual(config["api_key"], "test-anthropic-key")
        self.assertEqual(config["model"], "claude-3-haiku-20240307")
        self.assertTrue(config["is_configured"])

    def test_get_provider_config_anthropic_not_configured(self):
        """Test get_provider_config for anthropic without API key."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        config = get_provider_config(PROVIDER_ANTHROPIC)
        self.assertFalse(config["is_configured"])

    def test_is_provider_available_local_not_configured(self):
        """Test local provider not available when not configured."""
        # Local is always "configured" but may not be running
        # With empty LOCAL_LLM_BASE_URL, health check will fail
        os.environ["LOCAL_LLM_BASE_URL"] = ""
        
        # The function will try to connect and fail
        # This tests the behavior when local server is not running
        available = is_provider_available(PROVIDER_LOCAL)
        self.assertFalse(available)

    def test_is_provider_available_openai_compatible_configured(self):
        """Test openai_compatible provider is available when configured."""
        os.environ["HOSTED_LLM_BASE_URL"] = "https://router.huggingface.co/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-key"
        os.environ["HOSTED_LLM_MODEL"] = "openai/gpt-oss-120b"
        
        # Should return True without making HTTP requests
        available = is_provider_available(PROVIDER_OPENAI_COMPATIBLE)
        self.assertTrue(available)

    def test_is_provider_available_openai_compatible_not_configured(self):
        """Test openai_compatible provider not available when not configured."""
        for key in ["HOSTED_LLM_BASE_URL", "HOSTED_LLM_API_KEY", "HOSTED_LLM_MODEL"]:
            if key in os.environ:
                del os.environ[key]
        
        available = is_provider_available(PROVIDER_OPENAI_COMPATIBLE)
        self.assertFalse(available)

    def test_is_provider_available_anthropic_configured(self):
        """Test anthropic provider available when configured."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        
        available = is_provider_available(PROVIDER_ANTHROPIC)
        self.assertTrue(available)

    def test_is_provider_available_anthropic_not_configured(self):
        """Test anthropic provider not available when not configured."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        available = is_provider_available(PROVIDER_ANTHROPIC)
        self.assertFalse(available)

    def test_get_available_providers(self):
        """Test get_available_providers returns correct list."""
        # No providers configured
        available = get_available_providers()
        self.assertEqual(available, [])

    def test_get_available_providers_with_openai(self):
        """Test get_available_providers with openai configured."""
        os.environ["HOSTED_LLM_BASE_URL"] = "https://router.huggingface.co/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-key"
        os.environ["HOSTED_LLM_MODEL"] = "openai/gpt-oss-120b"
        
        available = get_available_providers()
        self.assertIn(PROVIDER_OPENAI_COMPATIBLE, available)

    def test_get_available_providers_with_anthropic(self):
        """Test get_available_providers with anthropic configured."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        
        available = get_available_providers()
        self.assertIn(PROVIDER_ANTHROPIC, available)

    def test_select_model_openai_compatible(self):
        """Test select_model with openai_compatible provider."""
        os.environ["HOSTED_LLM_BASE_URL"] = "https://router.huggingface.co/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-key"
        os.environ["HOSTED_LLM_MODEL"] = "openai/gpt-oss-120b"
        os.environ["DEFAULT_MODEL_PROVIDER"] = "openai_compatible"
        
        result = select_model("summary")
        self.assertEqual(result["provider"], PROVIDER_OPENAI_COMPATIBLE)
        self.assertEqual(result["model"], "openai/gpt-oss-120b")
        self.assertTrue(result["available"])
        self.assertFalse(result["fallback_used"])
        self.assertIsNone(result["error"])

    def test_select_model_with_preferred_provider(self):
        """Test select_model with explicit provider preference."""
        os.environ["HOSTED_LLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-key"
        os.environ["HOSTED_LLM_MODEL"] = "test-model"
        os.environ["ANTHROPIC_API_KEY"] = "anthropic-key"
        
        # Prefer anthropic when both available
        result = select_model("summary", preferred_provider=PROVIDER_ANTHROPIC)
        self.assertEqual(result["provider"], PROVIDER_ANTHROPIC)

    def test_select_model_unavailable_provider(self):
        """Test select_model with unavailable preferred provider."""
        # No providers configured
        for key in ["HOSTED_LLM_BASE_URL", "HOSTED_LLM_API_KEY", "HOSTED_LLM_MODEL",
                    "ANTHROPIC_API_KEY", "LOCAL_LLM_BASE_URL"]:
            if key in os.environ:
                del os.environ[key]
        
        result = select_model("summary", preferred_provider="openai_compatible")
        self.assertFalse(result["available"])
        self.assertIn("No providers available", result["error"])

    def test_select_model_unsupported_task(self):
        """Test select_model with unsupported task type."""
        os.environ["HOSTED_LLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-key"
        os.environ["HOSTED_LLM_MODEL"] = "test-model"
        
        result = select_model("unsupported_task")
        self.assertFalse(result["available"])
        self.assertIn("Unsupported task type", result["error"])

    def test_get_provider_status(self):
        """Test get_provider_status returns correct structure."""
        os.environ["HOSTED_LLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["HOSTED_LLM_API_KEY"] = "test-key"
        os.environ["HOSTED_LLM_MODEL"] = "test-model"
        os.environ["ANTHROPIC_API_KEY"] = "anthropic-key"
        os.environ["DEFAULT_MODEL_PROVIDER"] = "openai_compatible"
        
        status = get_provider_status()
        
        self.assertEqual(status["default"], "openai_compatible")
        self.assertIn(PROVIDER_OPENAI_COMPATIBLE, status["available_providers"])
        self.assertIn(PROVIDER_ANTHROPIC, status["available_providers"])
        
        # Check local provider structure
        self.assertIn(PROVIDER_LOCAL, status["providers"])
        self.assertTrue(status["providers"][PROVIDER_LOCAL]["configured"])
        
        # Check openai_compatible structure
        self.assertIn(PROVIDER_OPENAI_COMPATIBLE, status["providers"])
        self.assertTrue(status["providers"][PROVIDER_OPENAI_COMPATIBLE]["configured"])
        self.assertTrue(status["providers"][PROVIDER_OPENAI_COMPATIBLE]["available"])


if __name__ == "__main__":
    unittest.main()