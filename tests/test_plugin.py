import base64

import pytest
from platzky.plugin.plugin import ConfigPluginError

from platzky_promocode.plugin import PromocodeConfig, PromocodePlugin


def _make_plugin(**kwargs: object) -> PromocodePlugin:
    return PromocodePlugin({"color": "#ff0000", "text": "Get Code", **kwargs})


def _render(plugin: PromocodePlugin, content: str) -> str:
    """Apply the plugin's shortcode handler to content."""
    return plugin.transform_content(content)


# --- config ---


def test_defaults() -> None:
    plugin = PromocodePlugin({})
    assert plugin.config.color == "#4caf50"
    assert plugin.config.text == "Reveal Promo Code"


def test_invalid_color_rejected() -> None:
    with pytest.raises(ConfigPluginError):
        PromocodePlugin({"color": "javascript:alert(1)"})


@pytest.mark.parametrize("color", ["#fff", "#4caf50", "red", "rgb(0,0,0)", "rgba(0,0,0,0.5)"])
def test_valid_colors_accepted(color: str) -> None:
    plugin = PromocodePlugin({"color": color})
    assert isinstance(plugin.config, PromocodeConfig)


# --- shortcodes / shortcode dispatch ---


def test_tag_replaced_with_button() -> None:
    plugin = _make_plugin()
    result = _render(plugin, "[promocode]SAVE20[/promocode]")
    assert "platzky-promocode-btn" in result
    assert "SAVE20" not in result


def test_code_is_base64_encoded_in_button() -> None:
    import re

    plugin = _make_plugin()
    result = _render(plugin, "[promocode]SUMMER2024[/promocode]")
    match = re.search(r'data-code="([^"]+)"', result)
    assert match is not None
    assert base64.b64decode(match.group(1)).decode() == "SUMMER2024"


def test_multiple_tags_all_replaced() -> None:
    plugin = _make_plugin()
    result = _render(plugin, "[promocode]A[/promocode] and [promocode]B[/promocode]")
    assert result.count("platzky-promocode-btn") == 2


def test_content_without_tags_unchanged() -> None:
    plugin = _make_plugin()
    original = "<p>Hello world</p>"
    assert _render(plugin, original) == original


def test_button_color_from_config() -> None:
    plugin = _make_plugin(color="#abcdef")
    result = _render(plugin, "[promocode]CODE[/promocode]")
    assert "#abcdef" in result


def test_button_color_overridden_per_tag() -> None:
    plugin = _make_plugin(color="#abcdef")
    result = _render(plugin, '[promocode color="#123456"]CODE[/promocode]')
    assert "#123456" in result
    assert "#abcdef" not in result


def test_button_text_is_escaped() -> None:
    plugin = _make_plugin(text="<script>xss</script>")
    result = _render(plugin, "[promocode]CODE[/promocode]")
    assert "<script>" not in result


def test_shortcode_descriptor_has_metadata() -> None:
    plugin = _make_plugin()
    assert "promocode" in plugin.shortcodes
    sc = plugin.shortcodes["promocode"]
    assert sc.example
