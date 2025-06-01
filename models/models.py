"""
Centralized model configuration for all LLM providers.
"""

ANTHROPIC_MODELS = {
    "default": "claude-3-5-sonnet-20241022",
    # Add more Anthropic models here as needed
}

OPENAI_MODELS = {
    "default": "gpt-4o",
    # Add more OpenAI models here as needed
}

GEMINI_MODELS = {
    "default": "gemini-2.0-flash",
    # Add more Gemini models here as needed
}

def get_model(provider: str, name: str = "default") -> str:
    if provider == "anthropic":
        return ANTHROPIC_MODELS.get(name, ANTHROPIC_MODELS["default"])
    elif provider == "openai":
        return OPENAI_MODELS.get(name, OPENAI_MODELS["default"])
    elif provider == "gemini":
        return GEMINI_MODELS.get(name, GEMINI_MODELS["default"])
    else:
        raise ValueError(f"Unknown provider: {provider}")
