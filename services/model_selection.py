import os
import requests
from typing import Dict, Any


PROVIDER_LOCAL = "local"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDER_ANTHROPIC = "anthropic"

SUPPORTED_PROVIDERS = {
    PROVIDER_LOCAL,
    PROVIDER_OPENAI_COMPATIBLE,
    PROVIDER_ANTHROPIC
}

# Default provider - read at function call time via get_default_provider()
PROVIDER_LOCAL_STR = "local"
PROVIDER_OPENAI_COMPATIBLE_STR = "openai_compatible"
PROVIDER_ANTHROPIC_STR = "anthropic"

# Default model names (can be overridden via environment)
DEFAULT_LOCAL_MODEL = "qwen3-4b-q4_k_m"
DEFAULT_ANTHROPIC_MODEL = "claude-3-haiku-20240307"


def _get_env(key: str, default: str = "") -> str:
    """Get environment variable at call time."""
    return os.environ.get(key, default)


def get_default_provider() -> str:
    """Get default provider from environment at call time."""
    return _get_env("DEFAULT_MODEL_PROVIDER", PROVIDER_OPENAI_COMPATIBLE_STR)


def get_provider_config(provider: str) -> dict:
    """Get configuration for a provider at call time."""
    if provider == PROVIDER_LOCAL:
        return {
            "base_url": _get_env("LOCAL_LLM_BASE_URL", ""),
            "api_key": _get_env("LOCAL_LLM_API_KEY", "not-needed"),
            "model": _get_env("LOCAL_LLM_MODEL", DEFAULT_LOCAL_MODEL),
            "is_configured": True  # Local is always "configured" but may not be running
        }
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        base_url = _get_env("HOSTED_LLM_BASE_URL", "")
        api_key = _get_env("HOSTED_LLM_API_KEY", "")
        model = _get_env("HOSTED_LLM_MODEL", "")
        return {
            "base_url": base_url,
            "api_key": _get_env("HOSTED_LLM_API_KEY", ""),
            "model": _get_env("HOSTED_LLM_MODEL", ""),
            "is_configured": bool(base_url and api_key and model)
        }
    elif provider == PROVIDER_ANTHROPIC:
        return {
            "api_key": _get_env("ANTHROPIC_API_KEY", ""),
            "model": _get_env("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            "is_configured": bool(_get_env("ANTHROPIC_API_KEY", ""))
        }
    else:
        return {
            "is_configured": False
        }


def is_provider_available(provider: str) -> bool:
    """Check if a provider is available (configured and server reachable)."""
    config = get_provider_config(provider)
    
    if not config.get("is_configured"):
        return False
    
    if provider == PROVIDER_LOCAL:
        # Check if local server is reachable
        try:
            base_url = _get_env("LOCAL_LLM_BASE_URL", "")
            response = requests.get(f"{base_url.rstrip('/v1')}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            try:
                base_url = _get_env("LOCAL_LLM_BASE_URL", "")
                api_key = _get_env("LOCAL_LLM_API_KEY", "not-needed")
                response = requests.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=3
                )
                return response.status_code == 200
            except Exception:
                return False
    
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        # For hosted OpenAI-compatible providers (Hugging Face, Together.ai, etc.),
        # don't require a /health endpoint. If configured, consider available.
        # The actual API call will validate the configuration at request time.
        return True
    
    elif provider == PROVIDER_ANTHROPIC:
        # Anthropic doesn't have a simple health check
        return bool(_get_env("ANTHROPIC_API_KEY", ""))
    
    return False


def get_available_providers() -> list:
    """Return list of available providers based on configuration."""
    available = []
    for provider in SUPPORTED_PROVIDERS:
        if is_provider_available(provider):
            available.append(provider)
    return available


def select_model(task_type, preferred_provider=None):
    """
    Select the best provider/model for a given task.

    Args:
        task_type: One of "summary", "notes", "questions", "mcqs"
        preferred_provider: Optional provider hint ("local", "openai_compatible", "anthropic")

    Returns:
        dict: {
            "provider": str (one of SUPPORTED_PROVIDERS),
            "model": str (model identifier),
            "available": bool,
            "fallback_used": bool,
            "error": str or None
        }
    """
    if task_type not in {"summary", "notes", "questions", "mcqs"}:
        return {
            "provider": None,
            "model": None,
            "available": False,
            "fallback_used": False,
            "error": f"Unsupported task type: {task_type}"
        }

    available = get_available_providers()

    if not available:
        return {
            "provider": None,
            "model": None,
            "available": False,
            "fallback_used": False,
            "error": "No providers available. Configure LOCAL_LLM_BASE_URL, HOSTED_LLM_BASE_URL + HOSTED_LLM_API_KEY, or ANTHROPIC_API_KEY."
        }

    # If user explicitly requested a provider
    if preferred_provider:
        if preferred_provider in available:
            return _get_model_info(preferred_provider, task_type, fallback_used=False)
        elif preferred_provider in SUPPORTED_PROVIDERS:
            return {
                "provider": None,
                "model": None,
                "available": False,
                "fallback_used": False,
                "error": f"Requested provider '{preferred_provider}' is not available"
            }
        else:
            return {
                "provider": None,
                "model": None,
                "available": False,
                "fallback_used": False,
                "error": f"Unsupported provider: {preferred_provider}"
            }

    # Auto-select: prefer local if available, otherwise use first available
    if PROVIDER_LOCAL in available:
        return _get_model_info(PROVIDER_LOCAL, task_type, fallback_used=False)
    else:
        provider = available[0]
        return _get_model_info(provider, task_type, fallback_used=(provider != get_default_provider()))


def _get_model_info(provider, task_type, fallback_used):
    """Get model identifier for a provider."""
    config = get_provider_config(provider)
    
    return {
        "provider": provider,
        "model": config.get("model", "unknown"),
        "available": True,
        "fallback_used": fallback_used,
        "error": None
    }


def get_provider_status():
    """Get status of all providers."""
    return {
        "default": get_default_provider(),
        "available_providers": get_available_providers(),
        "providers": {
            PROVIDER_LOCAL: {
                "configured": True,
                "available": is_provider_available(PROVIDER_LOCAL),
                "model": _get_env("LOCAL_LLM_MODEL", "qwen3-4b-q4_k_m"),
                "base_url": _get_env("LOCAL_LLM_BASE_URL", "")
            },
            PROVIDER_OPENAI_COMPATIBLE: {
                "configured": bool(_get_env("HOSTED_LLM_BASE_URL", "") and _get_env("HOSTED_LLM_API_KEY", "") and _get_env("HOSTED_LLM_MODEL", "")),
                "available": is_provider_available(PROVIDER_OPENAI_COMPATIBLE),
                "model": _get_env("HOSTED_LLM_MODEL", ""),
                "base_url": _get_env("HOSTED_LLM_BASE_URL", "")
            },
            PROVIDER_ANTHROPIC: {
                "configured": bool(_get_env("ANTHROPIC_API_KEY", "")),
                "available": is_provider_available(PROVIDER_ANTHROPIC),
                "model": _get_env("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                "base_url": "https://api.anthropic.com"
            }
        }
    }


if __name__ == "__main__":
    # For testing
    print("Model selection module loaded")
    print(f"Available providers: {get_available_providers()}")