import sys
from .openai_provider import OpenAIProvider

_PROVIDERS = {
    "openai": OpenAIProvider,
}


def get_provider(name, **kwargs):
    provider_class = _PROVIDERS.get(name)
    if provider_class is None:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        print(
            f"Error: Unknown provider '{name}'. Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)
    return provider_class(**kwargs)
