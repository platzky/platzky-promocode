import base64
import re
from typing import cast
from unittest.mock import MagicMock

import pytest
from platzky.plugin.plugin import ConfigPluginError

from platzky_promocode.plugin import PromocodeConfig, PromocodePlugin


@pytest.fixture
def app_mock() -> MagicMock:
    mock = MagicMock()
    mock.jinja_env.globals = {}
    return mock


def _make_plugin(**kwargs: object) -> PromocodePlugin:
    return PromocodePlugin(
        {"promo_code": "SAVE20", "color": "#ff0000", "text": "Get Code", **kwargs}
    )


# --- config ---


def test_promo_code_is_required() -> None:
    with pytest.raises(ConfigPluginError):
        PromocodePlugin({})


def test_defaults() -> None:
    plugin = PromocodePlugin({"promo_code": "CODE"})
    config = cast(PromocodeConfig, plugin.config)
    assert config.color == "#4caf50"
    assert config.text == "Reveal Promo Code"


def test_invalid_color_rejected() -> None:
    with pytest.raises(ConfigPluginError):
        PromocodePlugin({"promo_code": "CODE", "color": "javascript:alert(1)"})


@pytest.mark.parametrize("color", ["#fff", "#4caf50", "red", "rgb(0,0,0)", "rgba(0,0,0,0.5)"])
def test_valid_colors_accepted(color: str) -> None:
    plugin = PromocodePlugin({"promo_code": "CODE", "color": color})
    assert isinstance(plugin.config, PromocodeConfig)


# --- process ---


def test_process_returns_app(app_mock: MagicMock) -> None:
    result = _make_plugin().process(app_mock)
    assert result is app_mock


def test_process_registers_field_plugin() -> None:
    assert PromocodePlugin.field_renderers["promo_code"] == "promocode"


def test_process_registers_blueprint(app_mock: MagicMock) -> None:
    _make_plugin().process(app_mock)
    app_mock.register_blueprint.assert_called_once()


def test_process_registers_manifest(app_mock: MagicMock) -> None:
    _make_plugin().process(app_mock)
    calls = [str(call) for call in app_mock.add_dynamic_head.call_args_list]
    assert any("PLUGIN_MANIFEST" in c and "promocode" in c for c in calls)


def test_process_injects_head(app_mock: MagicMock) -> None:
    _make_plugin().process(app_mock)
    all_injected = " ".join(str(c) for c in app_mock.add_dynamic_head.call_args_list)
    assert "platzkyRevealPromocode" in all_injected
    assert "platzky-promocode-btn" in all_injected


def test_process_registers_jinja_global(app_mock: MagicMock) -> None:
    _make_plugin().process(app_mock)
    assert "promocode_button" in app_mock.jinja_env.globals


def test_button_contains_encoded_code(app_mock: MagicMock) -> None:
    _make_plugin(promo_code="SUMMER2024").process(app_mock)
    html = str(app_mock.jinja_env.globals["promocode_button"]())
    match = re.search(r'data-code="([^"]+)"', html)
    assert match is not None
    assert base64.b64decode(match.group(1)).decode() == "SUMMER2024"


def test_button_does_not_expose_plain_code(app_mock: MagicMock) -> None:
    _make_plugin(promo_code="SECRET99").process(app_mock)
    html = str(app_mock.jinja_env.globals["promocode_button"]())
    assert "SECRET99" not in html


def test_button_contains_color(app_mock: MagicMock) -> None:
    _make_plugin(color="#abcdef").process(app_mock)
    html = str(app_mock.jinja_env.globals["promocode_button"]())
    assert "#abcdef" in html


def test_button_text_is_escaped(app_mock: MagicMock) -> None:
    _make_plugin(text="<script>xss</script>").process(app_mock)
    html = str(app_mock.jinja_env.globals["promocode_button"]())
    assert "<script>" not in html
