from unittest.mock import patch

import pytest
from babel import Locale
from markupsafe import Markup
from platzky.content_types import POST
from platzky.plugin.content_transformer import ContentTransformerRegistry
from platzky.plugin.plugin import ConfigPluginError
from platzky.shortcodes import ShortcodeAttrs

from platzky_promocode.plugin import PromocodeConfig, PromocodePlugin


def _make_plugin(**kwargs: object) -> PromocodePlugin:
    return PromocodePlugin({"color": "#ff0000", "text": "Get Code", **kwargs})


def _render(plugin: PromocodePlugin, content: str) -> str:
    """Render content the way the engine does: through the registry, behind the gate.

    A plugin never transforms content itself — ``ContentTransformerRegistry`` owns that,
    so a grant is part of rendering rather than something a test can skip. ``Markup``
    vouches for the content, as a post body is vouched for, leaving authored HTML intact
    and parsing tags strictly.
    """
    registry = ContentTransformerRegistry({POST})
    registry.grant(plugin, frozenset({POST}))
    return registry.transform_content([plugin], Markup(content), POST)


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


def test_tag_replaced_with_disclosure() -> None:
    plugin = _make_plugin()
    result = _render(plugin, "[promocode]SAVE20[/promocode]")
    assert "<details" in result
    assert "<summary>Get Code</summary>" in result
    assert "SAVE20" in result


def test_render_ships_no_script() -> None:
    """The control is native HTML: no handler, no script, nothing to serve."""
    plugin = _make_plugin()
    result = _render(plugin, "[promocode]SAVE20[/promocode]")
    assert "onclick" not in result
    assert "<script" not in result
    assert "atob" not in result


def test_multiple_tags_all_replaced() -> None:
    plugin = _make_plugin()
    result = _render(plugin, "[promocode]A[/promocode] and [promocode]B[/promocode]")
    assert result.count("<details") == 2


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


# --- accepted_content_types ---


def test_accepts_any_content_type_the_application_knows() -> None:
    """A promo code has no constraint on where it is revealed, so the operator decides.

    Asserted through the registry rather than on the attribute: the wildcard is resolved
    against the vocabulary in play, so a host's own content type is offered without this
    package having to know its name.
    """
    registry = ContentTransformerRegistry({"post", "page", "field", "catalogue_attr"})

    offered = registry.acceptable_content_types(PromocodePlugin({}))

    assert offered == {"post", "page", "field", "catalogue_attr"}


def test_wildcard_still_needs_an_operator_grant() -> None:
    """Accepting everything grants nothing: silence from the operator is still refusal."""
    registry = ContentTransformerRegistry({"post", "field"})
    plugin = PromocodePlugin({})

    assert not registry.may_transform(plugin, "field")

    registry.grant(plugin, frozenset({"field"}))

    assert registry.may_transform(plugin, "field")
    assert not registry.may_transform(plugin, "post")


# --- label locale resolution ---


def test_label_uses_matching_locale() -> None:
    plugin = PromocodePlugin({"text": {"en": "Reveal", "pl": "Pokaż"}})
    sc = plugin.shortcodes["promocode"]
    with patch("platzky_promocode.plugin.get_locale", return_value=Locale("pl")):
        assert "<summary>Pokaż</summary>" in sc.render_value("CODE")


def test_label_falls_back_to_first_key_for_an_unlisted_locale() -> None:
    plugin = PromocodePlugin({"text": {"en": "Reveal", "pl": "Pokaż"}})
    sc = plugin.shortcodes["promocode"]
    with patch("platzky_promocode.plugin.get_locale", return_value=Locale("uk")):
        assert "<summary>Reveal</summary>" in sc.render_value("CODE")


# --- render_value / html injection ---


def test_render_value_matches_the_tag_rendering() -> None:
    """One rendering, two entry points: a post and a marker popup cannot drift apart."""
    plugin = _make_plugin()
    sc = plugin.shortcodes["promocode"]
    assert sc.render_value("SAVE20") == _render(plugin, "[promocode]SAVE20[/promocode]")


def test_render_value_dict_matches_the_equivalent_tag() -> None:
    plugin = _make_plugin()
    sc = plugin.shortcodes["promocode"]
    from_field = sc.render_value({"code": "X", "color": "navy", "text": "Show"})
    from_tag = _render(plugin, '[promocode color="navy" text="Show"]X[/promocode]')
    assert from_field == from_tag


def test_text_attribute_overrides_the_configured_label() -> None:
    plugin = _make_plugin()
    assert "<summary>Show</summary>" in _render(plugin, '[promocode text="Show"]X[/promocode]')


def test_render_value_honours_dict_overrides() -> None:
    sc = _make_plugin().shortcodes["promocode"]
    result = sc.render_value({"code": "X", "color": "red", "text": "Pokaz"})
    assert "--platzky-promocode-color:red;" in result
    assert "<summary>Pokaz</summary>" in result


def test_render_value_escapes_hostile_code() -> None:
    sc = _make_plugin().shortcodes["promocode"]
    result = sc.render_value({"code": "<img src=x onerror=alert(1)>"})
    assert "<img" not in result
    assert "&lt;img" in result


def test_render_embeds_prose_content_without_escaping() -> None:
    """The other half of the contract: content from the trusted path is embedded as-is.

    A text filter or an inner shortcode earlier in the pipeline may have put markup in
    the code segment; escaping it here would show it to the reader as literal text.
    """
    sc = _make_plugin().shortcodes["promocode"]
    result = sc.render(ShortcodeAttrs(list(sc.attributes)), Markup("<b>SAVE</b>20"))

    assert "<b>SAVE</b>20" in result


def test_render_value_rejects_attribute_breakout_in_color() -> None:
    sc = _make_plugin().shortcodes["promocode"]
    result = sc.render_value({"code": "X", "color": 'red" onmouseover="alert(1)'})
    assert "onmouseover" not in result
    assert "--platzky-promocode-color:#ff0000;" in result


def test_entry_without_a_code_renders_an_empty_disclosure() -> None:
    """An incomplete entry must degrade to empty markup, never raise."""
    sc = _make_plugin().shortcodes["promocode"]
    assert sc.render_value({}) == sc.render_value("")


def test_head_html_is_a_style_block_only() -> None:
    head = _make_plugin().get_head_html()
    assert head.startswith("<style>")
    assert "<script" not in head


def test_plugin_accepts_head_section() -> None:
    assert "head" in PromocodePlugin.accepted_page_sections
