import os


PROVIDER_LOCAL = "local"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDER_ANTHROPIC = "anthropic"

SUPPORTED_PROVIDERS = {
    PROVIDER_LOCAL,
    PROVIDER_OPENAI_COMPATIBLE,
    PROVIDER_ANTHROPIC
}

DEFAULT_PROVIDER = os.environ.get("DEFAULT_MODEL_PROVIDER", PROVIDER_LOCAL)

# Local llama.cpp server (OpenAI-compatible mode)
LOCAL_LLM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:8080/v1")
LOCAL_LLM_API_KEY = os.environ.get("LOCAL_LLM_API_KEY", "not-needed")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "qwen3-4b-q4_k_m")

# Hosted OpenAI-compatible provider
HOSTED_LLM_BASE_URL = os.environ.get("HOSTED_LLM_BASE_URL", "")
HOSTED_LLM_API_KEY = os.environ.get("HOSTED_LLM_API_KEY", "")
HOSTED_LLM_MODEL = os.environ.get("HOSTED_LLM_MODEL", "")

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307")


def get_provider_config(provider: str) -> dict:
    """Get configuration for a provider."""
    if provider == PROVIDER_LOCAL:
        return {
            "base_url": LOCAL_LLM_BASE_URL,
            "api_key": LOCAL_LLM_API_KEY,
            "model": LOCAL_LLM_MODEL,
            "is_configured": True  # Local is always "configured" but may not be running
        }
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        return {
            "base_url": HOSTED_LLM_BASE_URL,
            "api_key": HOSTED_LLM_API_KEY,
            "model": HOSTED_LLM_MODEL,
            "is_configured": bool(HOSTED_LLM_BASE_URL and HOSTED_LLM_API_KEY and HOSTED_LLM_MODEL)
        }
    elif provider == PROVIDER_ANTHROPIC:
        return {
            "api_key": ANTHROPIC_API_KEY,
            "model": ANTHROPIC_MODEL,
            "is_configured": bool(ANTHROPIC_API_KEY)
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
        import requests
        try:
            response = requests.get(f"{config['base_url'].rstrip('/v1')}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            try:
                response = requests.get(
                    f"{config['base_url']}/models",
                    headers={"Authorization": f"Bearer {config['api_key']}"},
                    timeout=3
                )
                return response.status_code == 200
            except Exception:
                return False
    
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        import requests
        try:
            response = requests.get(
                f"{config['base_url'].rstrip('/v1')}/health",
                headers={"Authorization": f"Bearer {config['api_key']}"},
                timeout=3
            )
            return response.status_code == 200
        except Exception:
            try:
                response = requests.get(
                    f"{config['base_url']}/models",
                    headers={"Authorization": f"Bearer {config['api_key']}"},
                    timeout=3
                )
                return response.status_code == 200
            except Exception:
                return False
    
    elif provider == PROVIDER_ANTHROPIC:
        # Anthropic doesn't have a simple health check
        return bool(config.get("api_key"))
    
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
        return _get_model_info(provider, task_type, fallback_used=(provider != DEFAULT_PROVIDER))


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


def get_provider_config(provider: str) -> dict:
    """Get configuration for a provider (for internal use)."""
    if provider == PROVIDER_LOCAL:
        return {
            "base_url": LOCAL_LLM_BASE_URL,
            "api_key": LOCAL_LLM_API_KEY,
            "model": LOCAL_LLM_MODEL,
            "is_configured": True
        }
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        return {
            "base_url": HOSTED_LLM_BASE_URL,
            "api_key": HOSTED_LLM_API_KEY,
            "model": HOSTED_LLM_MODEL,
            "is_configured": bool(HOSTED_LLM_BASE_URL and HOSTED_LLM_API_KEY and HOSTED_LLM_MODEL)
        }
    elif provider == PROVIDER_ANTHROPIC:
        return {
            "api_key": ANTHROPIC_API_KEY,
            "model": ANTHROPIC_MODEL,
            "is_configured": bool(ANTHROPIC_API_KEY)
        }
    else:
        return {
            "is_configured": False
        }


def get_provider_status():
    """Get status of all providers."""
    return {
        "default": DEFAULT_PROVIDER,
        "available_providers": get_available_providers(),
        "providers": {
            PROVIDER_LOCAL: {
                "configured": True,
                "available": is_provider_available(PROVIDER_LOCAL),
                "model": LOCAL_LLM_MODEL,
                "base_url": LOCAL_LLM_BASE_URL
            },
            PROVIDER_OPENAI_COMPATIBLE: {
                "configured": bool(HOSTED_LLM_BASE_URL and HOSTED_LLM_API_KEY and HOSTED_LLM_MODEL),
                "available": is_provider_available(PROVIDER_OPENAI_COMPATIBLE),
                "model": HOSTED_LLM_MODEL,
                "base_url": HOSTED_LLM_BASE_URL
            },
            PROVIDER_ANTHROPIC: {
                "configured": bool(ANTHROPIC_API_KEY),
                "available": is_provider_available(PROVIDER_ANTHROPIC),
                "model": ANTHROPIC_MODEL,
                "base_url": "https://api.anthropic.com"
            }
        }
    }