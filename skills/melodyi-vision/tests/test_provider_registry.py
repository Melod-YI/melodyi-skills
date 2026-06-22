import pytest
from providers import get_provider
from providers.openai_provider import OpenAIProvider


class TestProviderRegistry:
    def test_get_openai_provider(self):
        provider = get_provider(
            "openai",
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
        )
        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_raises_system_exit(self):
        with pytest.raises(SystemExit):
            get_provider(
                "unknown_provider",
                api_key="test-key",
                api_base="https://api.openai.com/v1",
                model="gpt-4o",
                max_tokens=1024,
            )
