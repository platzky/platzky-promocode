"""Plugin for revealing promo codes embedded in blog content."""

import base64
import re
from typing import Any, ClassVar

from markupsafe import escape
from platzky.plugin.content_transformer import ContentTransformerPluginBase
from platzky.plugin.plugin import ConfigPluginError
from platzky.shortcodes import Shortcode, ShortcodeAttr, ShortcodeAttrs
from pydantic import BaseModel, ValidationError, field_validator

_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}"
    r"|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)"
    r"|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*[\d.]+\s*\)"
    r"|[a-zA-Z]+)$"
)


class PromocodeConfig(BaseModel):
    """Configuration for the Promocode plugin."""

    color: str = "#4caf50"
    text: str | dict[str, str] = "Reveal Promo Code"

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Reject values that are not valid CSS color literals."""
        if not _COLOR_RE.match(v.strip()):
            raise ValueError(f"Invalid CSS color: {v!r}")
        return v.strip()


class _PromocodeShortcode(Shortcode):
    """Shortcode that renders a reveal button for a promo code."""

    name = "promocode"
    description = "Reveal a promo code on click. Hidden until clicked."
    attributes: ClassVar[ShortcodeAttrs] = ShortcodeAttrs(
        [ShortcodeAttr("color", "Button colour (any CSS colour literal)", required=False)]
    )
    example = "[promocode]SUMMER2024[/promocode]"

    def __init__(self, config: PromocodeConfig) -> None:
        """Initialise with plugin config.

        Args:
            config: Plugin configuration supplying button text and default colour.
        """
        self._config = config

    def render(self, attrs: ShortcodeAttrs, content: str) -> str:
        """Render a reveal button for the promo code in content.

        Args:
            attrs: Parsed shortcode attributes; ``color`` overrides the configured colour.
            content: The promo code to encode.

        Returns:
            A ``<button>`` element that reveals the code on click.
        """
        code = content.strip()
        encoded = base64.b64encode(code.encode()).decode()
        text = self._config.text
        if isinstance(text, dict):
            from flask_babel import get_locale

            locale = str(get_locale())
            label = text.get(locale) or next(iter(text.values()))
        else:
            label = text
        safe_text = escape(label)
        color = (
            attrs.color.strip()
            if attrs.color and _COLOR_RE.match(attrs.color.strip())
            else self._config.color
        )
        return (
            f'<button class="platzky-promocode-btn"'
            f' style="--platzky-promocode-color:{color};"'
            f' data-code="{encoded}"'
            f' onclick="platzkyRevealPromocode(this)">'
            f"{safe_text}"
            f"</button>"
        )


class PromocodePlugin(ContentTransformerPluginBase):
    """Plugin that registers a ``[promocode]`` shortcode.

    Blog authors embed promo codes in post content as::

        [promocode]SAVE20[/promocode]

    An optional ``color`` attribute overrides the configured button colour::

        [promocode color="#e91e63"]SAVE20[/promocode]

    The actual code is base64-encoded in a ``data-code`` attribute and decoded
    client-side via ``atob()`` so it is never present as plain text in the DOM.
    """

    shortcodes: ClassVar[dict[str, Shortcode]] = {}

    def __init__(self, _config: dict[str, Any]) -> None:
        """Initialise the plugin, parse config, and build the shortcode registry.

        Args:
            _config: Raw configuration dict from the platzky engine.

        Raises:
            ConfigPluginError: If the configuration is invalid.
        """
        super().__init__(_config)
        try:
            config = PromocodeConfig.model_validate(_config)
        except ValidationError as e:
            raise ConfigPluginError(f"Invalid configuration: {e}") from e
        self.shortcodes = {"promocode": _PromocodeShortcode(config)}  # type: ignore[misc]
        self.config = config


Plugin = PromocodePlugin
