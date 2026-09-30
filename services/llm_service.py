import os
import json
import requests
from typing import Dict, Any, Optional


# Provider types
PROVIDER_LOCAL = "local"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDER_ANTHROPIC = "anthropic"

SUPPORTED_PROVIDERS = {
    PROVIDER_LOCAL,
    PROVIDER_OPENAI_COMPATIBLE,
    PROVIDER_ANTHROPIC
}

# Default model names (can be overridden via environment)
DEFAULT_LOCAL_MODEL = "qwen3-4b-q4_k_m"
DEFAULT_ANTHROPIC_MODEL = "claude-3-haiku-20240307"


def _get_env(key: str, default: str = "") -> str:
    """Get environment variable at call time."""
    return os.environ.get(key, default)


def get_provider_config(provider: str) -> Dict[str, Any]:
    """Get configuration for a provider at call time."""
    if provider == PROVIDER_LOCAL:
        return {
            "base_url": os.environ.get("LOCAL_LLM_BASE_URL", ""),
            "api_key": os.environ.get("LOCAL_LLM_API_KEY", "not-needed"),
            "model": os.environ.get("LOCAL_LLM_MODEL", "qwen3-4b-q4_k_m"),
            "timeout": int(os.environ.get("LOCAL_LLM_TIMEOUT", "300")),
            "max_tokens": int(os.environ.get("LOCAL_LLM_MAX_TOKENS", "4096")),
            "is_configured": True  # Local is always "configured" but may not be running
        }
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        base_url = os.environ.get("HOSTED_LLM_BASE_URL", "")
        api_key = os.environ.get("HOSTED_LLM_API_KEY", "")
        model = os.environ.get("HOSTED_LLM_MODEL", "")
        return {
            "base_url": base_url,
            "api_key": os.environ.get("HOSTED_LLM_API_KEY", ""),
            "model": os.environ.get("HOSTED_LLM_MODEL", ""),
            "timeout": int(os.environ.get("HOSTED_LLM_TIMEOUT", "120")),
            "max_tokens": int(os.environ.get("HOSTED_LLM_MAX_TOKENS", "4096")),
            "is_configured": bool(base_url and api_key and model)
        }
    elif provider == PROVIDER_ANTHROPIC:
        return {
            "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            "timeout": int(os.environ.get("ANTHROPIC_TIMEOUT", "120")),
            "max_tokens": int(os.environ.get("ANTHROPIC_MAX_TOKENS", "4096")),
            "is_configured": bool(os.environ.get("ANTHROPIC_API_KEY", ""))
        }
    else:
        return {
            "is_configured": False
        }


# System prompts for each task type (used as system message in chat format)
TASK_SYSTEM_PROMPTS = {
    "summary": """You are a helpful assistant that creates concise, well-structured summaries of lecture content using Markdown formatting.

Given the lecture content below, write a clear and well-structured summary that captures the key concepts, main ideas, and important details.

Format your response using Markdown:
- Use ## for section headings
- Use **bold** for emphasis on key terms
- Use bullet points for lists
- Use numbered lists for sequential items
- Use tables for comparisons if appropriate
- Use `inline code` for technical terms
- Use --- for horizontal rules between major sections

The summary should be:
- Organized with clear sections
- Concise but comprehensive
- Written in plain language suitable for studying
- Grounded ONLY in the provided lecture content""",
    
    "notes": """You are a helpful assistant that creates detailed, structured study notes from lecture content using Markdown formatting.

Given the lecture content below, create comprehensive study notes that a student could use for revision.

Format your response using Markdown:
- Use # for the main title
- Use ## for major section headings
- Use ### for subsections
- Use **bold** for key terms and definitions
- Use bullet points (- ) for lists
- Use numbered lists (1. ) for sequential steps
- Use tables (| |) for comparisons, data types, ranges, etc.
- Use `inline code` for technical terms, keywords, syntax
- Use fenced code blocks (```) for code examples
- Use > blockquotes for important notes/warnings
- Use --- for horizontal rules between major topics

The notes should include:
- Clear headings and subheadings for each topic
- Key definitions and concepts
- Examples from the lecture where present
- Important formulas, ranges, syntax rules
- Tables for comparisons (data types, sizes, ranges, etc.)
- Key points highlighted
- Structured for effective studying and revision
- Grounded ONLY in the provided lecture content

Generate COMPLETE notes - do not stop mid-sentence or mid-section.""",
    
    "questions": """You are a helpful assistant that generates study questions with answers from lecture content using Markdown formatting.

Given the lecture content below, create a set of practice questions that test understanding of the material.

Format your response using Markdown:
- Use ## for the title "Study Questions"
- Use ### for each question
- Use **Question:** followed by the question text
- Use **Answer:** followed by the complete answer
- Use bullet points for multi-part answers
- Use `inline code` for technical terms

The questions should:
- Cover different levels (recall, comprehension, application)
- Be specific to the lecture content provided
- Have clear, complete answers
- Be numbered sequentially (Q1, Q2, Q3, ...)
- Grounded ONLY in the provided lecture content

Generate COMPLETE questions and answers - do not stop mid-answer.""",
    
    "mcqs": """You are a helpful assistant that generates multiple-choice questions (MCQs) from lecture content using Markdown formatting.

Given the lecture content below, create multiple-choice questions for practice and self-assessment.

Format your response using Markdown:
- Use ## for the title "Multiple Choice Questions"
- Each MCQ must be clearly separated
- Use ### for each question (e.g., ### Q1. Question text)
- Present options as a bullet list:
  - **A.** Option text
  - **B.** Option text
  - **C.** Option text
  - **D.** Option text
- Use **Correct Answer:** followed by the letter and option text
- Use **Explanation:** followed by a brief explanation

Example format:
### Q1. Which of the following is a primitive data type in Java?

- **A.** String
- **B.** Array
- **C.** int
- **D.** Class

**Correct Answer:** C. int

**Explanation:** int is one of Java's eight primitive data types.

Requirements:
- Each MCQ has exactly 4 options (A, B, C, D)
- Only ONE correct answer
- Correct answer clearly indicated
- Brief explanation provided
- Questions specific to lecture content
- Numbered sequentially (Q1, Q2, Q3, ...)
- Grounded ONLY in the provided lecture content

Generate COMPLETE MCQs - do not stop mid-question or mid-explanation.""",
}

# User prompt template (same for all tasks - just includes the context)
USER_PROMPT_TEMPLATE = """LECTURE CONTENT:
{context}

Please generate the requested study material using Markdown formatting. Generate the COMPLETE response without stopping mid-way."""


def get_provider_config(provider: str) -> Dict[str, Any]:
    """Get configuration for a provider at call time."""
    if provider == PROVIDER_LOCAL:
        return {
            "base_url": os.environ.get("LOCAL_LLM_BASE_URL", ""),
            "api_key": os.environ.get("LOCAL_LLM_API_KEY", "not-needed"),
            "model": os.environ.get("LOCAL_LLM_MODEL", "qwen3-4b-q4_k_m"),
            "timeout": int(os.environ.get("LOCAL_LLM_TIMEOUT", "300")),
            "max_tokens": int(os.environ.get("LOCAL_LLM_MAX_TOKENS", "4096")),
            "is_configured": True  # Local is always "configured" but may not be running
        }
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        base_url = os.environ.get("HOSTED_LLM_BASE_URL", "")
        api_key = os.environ.get("HOSTED_LLM_API_KEY", "")
        model = os.environ.get("HOSTED_LLM_MODEL", "")
        return {
            "base_url": base_url,
            "api_key": os.environ.get("HOSTED_LLM_API_KEY", ""),
            "model": os.environ.get("HOSTED_LLM_MODEL", ""),
            "timeout": int(os.environ.get("HOSTED_LLM_TIMEOUT", "120")),
            "max_tokens": int(os.environ.get("HOSTED_LLM_MAX_TOKENS", "4096")),
            "is_configured": bool(base_url and api_key and model)
        }
    elif provider == PROVIDER_ANTHROPIC:
        return {
            "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            "timeout": int(os.environ.get("ANTHROPIC_TIMEOUT", "120")),
            "max_tokens": int(os.environ.get("ANTHROPIC_MAX_TOKENS", "4096")),
            "is_configured": bool(os.environ.get("ANTHROPIC_API_KEY", ""))
        }
    else:
        return {
            "is_configured": False
        }


def is_provider_available(provider: str) -> bool:
    """Check if a provider is configured and available."""
    config = get_provider_config(provider)
    
    if not config.get("is_configured"):
        return False
    
    if provider == "local":
        # Check if local server is reachable
        try:
            base_url = os.environ.get("LOCAL_LLM_BASE_URL", "")
            response = requests.get(f"{base_url.rstrip('/v1')}/health", timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass  # Fall through to /models endpoint
        
        # Fallback to /models endpoint
        try:
            base_url = os.environ.get("LOCAL_LLM_BASE_URL", "")
            api_key = os.environ.get("LOCAL_LLM_API_KEY", "not-needed")
            response = requests.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    elif provider == "openai_compatible":
        # For hosted OpenAI-compatible providers (Hugging Face, Together.ai, etc.),
        # don't require a /health endpoint. If configured, consider available.
        # The actual API call will validate the configuration at request time.
        return True
    
    elif provider == "anthropic":
        # Anthropic doesn't have a simple health check, just check API key
        return bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    
    return False


def get_available_providers() -> list:
    """Return list of available providers based on configuration."""
    available = []
    for provider in ["local", "openai_compatible", "anthropic"]:
        if is_provider_available(provider):
            available.append(provider)
    return available


def call_openai_compatible_chat(system_prompt: str, user_prompt: str, config: Dict[str, Any], temperature: float = 0.3) -> Dict[str, Any]:
    """Call an OpenAI-compatible chat completions API (local llama.cpp server or hosted provider)."""
    try:
        max_tokens = config.get("max_tokens", 4096)
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
            "stream": False,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }

        response = requests.post(
            f"{config['base_url'].rstrip('/')}/chat/completions",
            json=payload,
            timeout=config["timeout"],
            headers=headers
        )

        if response.status_code != 200:
            return {
                "success": False,
                "text": None,
                "error": f"API returned {response.status_code}: {response.text}"
            }

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return {
                "success": False,
                "text": None,
                "error": "API returned no choices"
            }

        message = choices[0].get("message", {})
        text = message.get("content", "").strip()

        if not text:
            return {
                "success": False,
                "text": None,
                "error": "API returned empty response"
            }

        return {
            "success": True,
            "text": text,
            "error": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "text": None,
            "error": f"Cannot connect to API at {config['base_url']}. Make sure the server is running."
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "text": None,
            "error": f"API timed out after {config['timeout']} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "text": None,
            "error": f"Error calling API: {str(e)}"
        }


def call_anthropic(prompt: str, config: Dict[str, Any], temperature: float = 0.3) -> Dict[str, Any]:
    """Call Anthropic API."""
    try:
        max_tokens = config.get("max_tokens", 4096)
        payload = {
            "model": config["model"],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01"
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            timeout=config["timeout"],
            headers=headers
        )

        if response.status_code != 200:
            return {
                "success": False,
                "text": None,
                "error": f"Anthropic API returned {response.status_code}: {response.text}"
            }

        data = response.json()
        content = data.get("content", [])
        if not content:
            return {
                "success": False,
                "text": None,
                "error": "Anthropic returned no content"
            }

        text = content[0].get("text", "").strip()

        if not text:
            return {
                "success": False,
                "text": None,
                "error": "Anthropic returned empty response"
            }

        return {
            "success": True,
            "text": text,
            "error": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "text": None,
            "error": "Cannot connect to Anthropic API"
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "text": None,
            "error": f"Anthropic API timed out after {config['timeout']} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "text": None,
            "error": f"Error calling Anthropic: {str(e)}"
        }


def generate_study_material(task_type: str, context: str, provider: str = None) -> Dict[str, Any]:
    """
    Generate study material using the selected provider.

    Args:
        task_type: One of "summary", "notes", "questions", "mcqs"
        context: Retrieved lecture context from RAG
        provider: Optional provider override

    Returns:
        Dict with 'success', 'content', 'error', 'provider', 'model' keys
    """
    if task_type not in TASK_SYSTEM_PROMPTS:
        return {
            "success": False,
            "content": None,
            "error": f"Unsupported task type: {task_type}",
            "provider": None,
            "model": None
        }

    if not context or not context.strip():
        return {
            "success": False,
            "content": None,
            "error": "No lecture context provided",
            "provider": None,
            "model": None
        }

    # Determine provider
    if provider is None:
        provider = "openai_compatible"

    if provider not in ["local", "openai_compatible", "anthropic"]:
        return {
            "success": False,
            "content": None,
            "error": f"Unsupported provider: {provider}",
            "provider": None,
            "model": None
        }

    config = get_provider_config(provider)
    
    if not config.get("is_configured"):
        return {
            "success": False,
            "content": None,
            "error": f"Provider '{provider}' is not configured. Check environment variables.",
            "provider": None,
            "model": None
        }

    # Check availability (server reachable)
    if not is_provider_available(provider):
        return {
            "success": False,
            "content": None,
            "error": f"Provider '{provider}' is not available. Check server/API status.",
            "provider": provider,
            "model": config.get("model")
        }

    system_prompt = TASK_SYSTEM_PROMPTS[task_type]
    user_prompt = USER_PROMPT_TEMPLATE.format(context=context)

    # Call the appropriate provider
    if provider in ("local", "openai_compatible"):
        result = call_openai_compatible_chat(system_prompt, user_prompt, config)
    elif provider == "anthropic":
        # For Anthropic, combine system + user into a single prompt (Anthropic uses messages array)
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        result = call_anthropic(combined_prompt, config)
    else:
        return {
            "success": False,
            "content": None,
            "error": f"Unknown provider: {provider}",
            "provider": provider,
            "model": config.get("model")
        }

    if not result["success"]:
        return {
            "success": False,
            "content": None,
            "error": result["error"],
            "provider": provider,
            "model": config.get("model")
        }

    return {
        "success": True,
        "content": result["text"],
        "error": None,
        "provider": provider,
        "model": config.get("model")
    }


def get_llm_service_status() -> Dict[str, Any]:
    """Get status of all LLM providers."""
    status = {
        "default_provider": "openai_compatible",
        "providers": {}
    }

    for provider in ["local", "openai_compatible", "anthropic"]:
        config = get_provider_config(provider)
        available = is_provider_available(provider) if config.get("is_configured") else False
        
        status["providers"][provider] = {
            "configured": config.get("is_configured", False),
            "available": available,
            "model": config.get("model"),
            "base_url": config.get("base_url") if provider in ("local", "openai_compatible") else None,
            "error": None if available else (f"Provider '{provider}' not available" if config.get("is_configured") else f"Provider '{provider}' not configured")
        }

    return status