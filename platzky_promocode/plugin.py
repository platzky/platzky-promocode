"""Plugin for revealing promo codes embedded in blog content."""

import re
from collections.abc import Mapping
from typing import Any, ClassVar

from flask_babel import get_locale, gettext  # type: ignore[reportUnknownVariableType]
from markupsafe import Markup, escape
from platzky.content_types import ALL_CONTENT_TYPES, ContentType
from platzky.plugin.content_transformer import ContentTransformerPluginBase
from platzky.plugin.html_injector import HtmlInjectorPluginBase, PageSection
from platzky.plugin.plugin import ConfigPluginError
from platzky.shortcodes import Shortcode, ShortcodeAttr, ShortcodeAttrs
from pydantic import BaseModel, ValidationError, field_validator

_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}"
    r"|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)"
    r"|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*[\d.]+\s*\)"
    r"|[a-zA-Z]+)$"
)

# Styles the native disclosure as a button and swaps it for the code once open. The
# colour arrives per element as a custom property, so these rules are static and can be
# injected once into <head> rather than inlined on every occurrence.
_STYLE = """<style>
.platzky-promocode{display:inline-block}
.platzky-promocode>summary{
background:var(--platzky-promocode-color,#4caf50);border-radius:4px;color:#fff;
cursor:pointer;display:inline-block;list-style:none;padding:.5rem 1.25rem;
user-select:none}
.platzky-promocode>summary::-webkit-details-marker{display:none}
.platzky-promocode[open]{
background:#333;border-radius:4px;color:#fff;font-family:monospace;
letter-spacing:.1em;padding:.5rem 1.25rem}
.platzky-promocode[open]>summary{display:none}
</style>"""


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
        [
            ShortcodeAttr("color", "Button colour (any CSS colour literal)", required=False),
            ShortcodeAttr("text", "Button label, overriding the configured one", required=False),
        ]
    )
    example = "[promocode]SUMMER2024[/promocode]"
    # A promocode field keeps the code under `code`, so that is its inner content.
    content_key: ClassVar[str] = "code"

    def __init__(self, config: PromocodeConfig) -> None:
        """Initialise with plugin config.

        Args:
            config: Plugin configuration supplying button text and default colour.
        """
        self._config = config

    def _resolve_label(self) -> str:
        """Return the localised button label from config text or dict mapping."""
        text = self._config.text
        if isinstance(text, dict):
            locale = str(get_locale())
            return text.get(locale) or next(iter(text.values()))
        return gettext(text)

    def render(self, attrs: ShortcodeAttrs, content: Markup) -> str:
        """Render the reveal control, for a tag in post content or for a field value.

        The only rendering this shortcode has: ``render_value`` maps a field value onto
        these arguments (``code`` is the ``content_key``, ``color`` and ``text`` are
        declared attributes), so a post and a field value cannot drift apart, and
        ``color`` is validated here once for both.

        ``<details>`` is the native click-to-reveal control, so the button needs no
        script: it is keyboard-operable and screen-reader-correct on its own, survives a
        strict CSP, and still works in a host that strips event handlers.

        Args:
            attrs: Parsed attributes; ``color`` and ``text`` override the configured ones.
                Raw, so ``color`` and ``label`` are escaped where they are interpolated.
            content: The promo code to reveal. ``Markup`` because the escaping decision
                is already made upstream — a stored value was escaped by ``render_value``,
                and post content was vouched for by its caller — so escaping it again here
                would only mangle it.

        Returns:
            A ``<details>`` element revealing the code on click.
        """
        color = attrs.color.strip()
        if not _COLOR_RE.match(color):
            color = self._config.color
        label = attrs.text or self._resolve_label()
        return (
            f'<details class="platzky-promocode"'
            f' style="--platzky-promocode-color:{color};">'
            f"<summary>{escape(label)}</summary>"
            f"{content.strip()}"
            f"</details>"
        )


class PromocodePlugin(ContentTransformerPluginBase, HtmlInjectorPluginBase):
    """Plugin that registers a ``[promocode]`` shortcode.

    Blog authors embed promo codes in post content as::

        [promocode]SAVE20[/promocode]

    An optional ``color`` attribute overrides the configured button colour::

        [promocode color="#e91e63"]SAVE20[/promocode]

    The control is a native ``<details>`` disclosure, so the plugin ships no JavaScript
    at all: the reveal works under a strict CSP, in a host that strips event handlers,
    and for keyboard and screen-reader users without any scripted behaviour. The code is
    plain text in the markup — base64 never concealed it either, since the field payload
    carries it in the API response.

    It accepts any content type, so a host that maps one of its own content fields to this
    shortcode gets the same control from ``render_value`` — whichever content types the
    operator grants.

    The one thing the markup needs is a stylesheet, injected into ``<head>`` so the same
    rules serve every page and every host.
    """

    # No technical constraint on where a code can be revealed, so the operator decides
    # entirely — including for content types that did not exist when this was written.
    accepted_content_types: Mapping[ContentType, str] = {
        ALL_CONTENT_TYPES: (
            "Reveals a promo code wherever one is worth showing. The control is inert "
            "markup — no script, no network, nothing that costs anything to render — so "
            "there is no kind of content it is unsuited to."
        )
    }
    accepted_page_sections: frozenset[PageSection] = frozenset({"head"})
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

    def get_head_html(self) -> str:
        """Return the stylesheet that makes the disclosure look like a button.

        Returns:
            A ``<style>`` block scoped to this plugin's own class name.
        """
        return _STYLE


Plugin = PromocodePlugin
