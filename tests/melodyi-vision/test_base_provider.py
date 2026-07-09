"""Tests for the BaseProvider abstract class."""
import pytest
from providers.base import BaseProvider


class TestBaseProvider:
    """Tests that enforce the BaseProvider contract."""

    def test_cannot_instantiate_directly(self):
        """BaseProvider is abstract and must not be instantiated directly."""
        with pytest.raises(TypeError):
            BaseProvider()

    def test_concrete_subclass_must_implement_understand(self):
        """A subclass that does not implement understand() cannot be instantiated."""

        class IncompleteProvider(BaseProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_concrete_subclass_can_be_instantiated(self):
        """A subclass that implements understand() can be instantiated."""

        class CompleteProvider(BaseProvider):
            def understand(self, image_data: str, mime_type: str, prompt: str) -> str:
                return "understood"

        provider = CompleteProvider()
        assert isinstance(provider, BaseProvider)
        assert provider.understand("data", "image/png", "describe") == "understood"
