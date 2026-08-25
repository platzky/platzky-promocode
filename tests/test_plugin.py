import base64
from unittest.mock import patch

import pytest
from babel import Locale
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


# --- text dict / i18n ---


def test_text_dict_uses_matching_locale() -> None:
    plugin = PromocodePlugin({"text": {"en": "Reveal", "pl": "Pokaż"}})
    with patch("platzky_promocode.plugin.get_locale", return_value=Locale("pl")):
        result = _render(plugin, "[promocode]CODE[/promocode]")
    assert "Pokaż" in result


def test_text_dict_falls_back_to_first_key_when_no_match() -> None:
    plugin = PromocodePlugin({"text": {"en": "Reveal", "pl": "Pokaż"}})
    with patch("platzky_promocode.plugin.get_locale", return_value=Locale("uk")):
        result = _render(plugin, "[promocode]CODE[/promocode]")
    assert "Reveal" in result


def test_text_str_used_literally() -> None:
    plugin = PromocodePlugin({"text": "Custom label"})
    result = _render(plugin, "[promocode]CODE[/promocode]")
    assert "Custom label" in result


# --- transform_field_value ---


def test_transform_field_value_plain_string() -> None:
    plugin = PromocodePlugin({"color": "#ff0000", "text": "Get Code"})
    sc = plugin.shortcodes["promocode"]
    result = sc.transform_field_value("SUMMER24")
    assert result == {
        "scope": "promocode",
        "color": "#ff0000",
        "text": "Get Code",
        "code": "U1VNTUVSMjQ=",
    }


def test_transform_field_value_dict_with_overrides() -> None:
    plugin = PromocodePlugin({"color": "#ff0000", "text": "Get Code"})
    sc = plugin.shortcodes["promocode"]
    result = sc.transform_field_value({"code": "SUMMER24", "color": "red", "text": "custom"})
    assert result["code"] == "U1VNTUVSMjQ="
    assert result["color"] == "red"
    assert result["text"] == "custom"
    assert result["scope"] == "promocode"


def test_transform_field_value_dict_falls_back_to_config_defaults() -> None:
    plugin = PromocodePlugin({"color": "#ff0000", "text": "Get Code"})
    sc = plugin.shortcodes["promocode"]
    result = sc.transform_field_value({"code": "X"})
    assert result["color"] == "#ff0000"
    assert result["text"] == "Get Code"


# --- accepted_content_types ---


def test_accepted_content_types_includes_field() -> None:
    assert "field" in PromocodePlugin.accepted_content_types


# --- transform_field_value locale resolution ---


def test_transform_field_value_dict_text_uses_matching_locale() -> None:
    plugin = PromocodePlugin({"text": {"en": "Reveal", "pl": "Pokaż"}})
    sc = plugin.shortcodes["promocode"]
    with patch("platzky_promocode.plugin.get_locale", return_value=Locale("pl")):
        result = sc.transform_field_value("CODE")
    assert result["text"] == "Pokaż"


def test_transform_field_value_dict_text_falls_back_to_first_key() -> None:
    plugin = PromocodePlugin({"text": {"en": "Reveal", "pl": "Pokaż"}})
    sc = plugin.shortcodes["promocode"]
    with patch("platzky_promocode.plugin.get_locale", return_value=Locale("uk")):
        result = sc.transform_field_value("CODE")
    assert result["text"] == "Reveal"
