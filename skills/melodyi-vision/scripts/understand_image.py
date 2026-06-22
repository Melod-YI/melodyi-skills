import argparse
import sys

from config import load_config
from image_utils import load_image
from providers import get_provider

DEFAULT_PROMPT = "Describe this image in detail."


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Understand an image using a vision-capable API."
    )
    parser.add_argument("image_source", help="Local file path or URL of the image")
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help=f"Custom question about the image (default: '{DEFAULT_PROMPT}')",
    )
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--provider", help="Override provider from config")
    parser.add_argument("--model", help="Override model from config")
    parser.add_argument(
        "--max-tokens", type=int, help="Override max_tokens from config"
    )
    return parser.parse_args(args)


def main(args=None):
    parsed = parse_args(args)

    cli_overrides = {
        "provider": parsed.provider,
        "model": parsed.model,
        "max_tokens": parsed.max_tokens,
    }
    config = load_config(
        cli_overrides=cli_overrides,
        config_path=parsed.config,
    )

    image_data, mime_type = load_image(parsed.image_source)

    provider = get_provider(
        config.provider,
        api_key=config.api_key,
        api_base=config.api_base,
        model=config.model,
        max_tokens=config.max_tokens,
    )

    result = provider.understand(image_data, mime_type, parsed.prompt)
    print(result)


if __name__ == "__main__":
    main()
