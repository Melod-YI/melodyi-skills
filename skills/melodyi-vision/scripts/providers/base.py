"""Abstract base class for image-understanding providers."""
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Base class that all vision-API providers must subclass.

    Each provider must implement the ``understand`` method, which accepts
    base64-encoded image data, its MIME type, and a text prompt, and returns
    a text description of the image.
    """

    @abstractmethod
    def understand(self, image_data: str, mime_type: str, prompt: str) -> str:
        """Analyze an image and return a text description.

        Args:
            image_data: Base64-encoded image bytes.
            mime_type:  MIME type of the image (e.g. ``image/png``).
            prompt:     A text prompt guiding what to describe.

        Returns:
            A textual description of the image.
        """
