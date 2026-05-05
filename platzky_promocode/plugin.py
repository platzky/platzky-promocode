"""Plugin for revealing promo codes."""

import base64
import re
from typing import Any

from flask import Blueprint
from goodmap.plugin import GoodmapPlugin
from markupsafe import Markup, escape
from platzky.engine import Engine
from platzky.plugin.plugin import PluginBaseConfig
from pydantic import field_validator

_CSS_JS = """
<style>
.platzky-promocode-btn {
    background-color: var(--platzky-promocode-color, #4caf50);
    border: none;
    border-radius: 4px;
    color: #fff;
    cursor: pointer;
    font-size: 1rem;
    padding: 0.5rem 1.25rem;
    transition: opacity 0.2s;
}
.platzky-promocode-btn:hover { opacity: 0.85; }
.platzky-promocode-btn.revealed {
    background-color: #333;
    cursor: default;
    font-family: monospace;
    letter-spacing: 0.1em;
}
</style>
<script>
function platzkyRevealPromocode(btn) {
    btn.textContent = atob(btn.dataset.code);
    btn.classList.add('revealed');
    btn.onclick = null;
}
</script>
"""

_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}"
    r"|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)"
    r"|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*[\d.]+\s*\)"
    r"|[a-zA-Z]+)$"
)

_MF_SCOPE = "promocode"
_MF_MODULE = "./Button"
_MF_URL = f"/plugins/{_MF_SCOPE}/remoteEntry.js"


class PromocodeConfig(PluginBaseConfig):
    """Configuration for the Promocode plugin."""

    color: str = "#4caf50"
    text: str = "Reveal Promo Code"
    promo_code: str

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Reject values that are not valid CSS color literals."""
        if not _COLOR_RE.match(v.strip()):
            raise ValueError(f"Invalid CSS color: {v!r}")
        return v.strip()


class PromocodePlugin(GoodmapPlugin[PromocodeConfig]):
    """Goodmap plugin that renders a click-to-reveal promo code button."""

    field_renderers = {"promo_code": _MF_SCOPE}

    @classmethod
    def get_config_model(cls) -> type[PromocodeConfig]:
        """Return the config model class for this plugin."""
        return PromocodeConfig

    def process(self, app: Engine) -> Engine:
        """Register MF remote, static files, CSS/JS, and Jinja2 global."""
        app = super().process(app)
        assert isinstance(self.config, PromocodeConfig)
        config = self.config

        # Serve the compiled MF remote entry from the package's static/ directory.
        blueprint = Blueprint(
            "platzky_promocode",
            __name__,
            static_folder="static",
            static_url_path=f"/plugins/{_MF_SCOPE}",
        )
        app.register_blueprint(blueprint)

        app.add_dynamic_head(
            f"<script>"
            f"window.PLUGIN_MANIFEST=window.PLUGIN_MANIFEST||[];"
            f'window.PLUGIN_MANIFEST.push({{scope:"{_MF_SCOPE}",url:"{_MF_URL}",module:"{_MF_MODULE}"}});'
            f"</script>"
        )
        app.add_dynamic_head(_CSS_JS)

        encoded = base64.b64encode(config.promo_code.encode()).decode()
        safe_text = escape(config.text)
        button_html = Markup(
            f'<button class="platzky-promocode-btn" '
            f'style="--platzky-promocode-color:{config.color};" '
            f'data-code="{encoded}" '
            f'onclick="platzkyRevealPromocode(this)">'
            f"{safe_text}"
            f"</button>"
        )
        jinja_globals: dict[str, Any] = app.jinja_env.globals
        jinja_globals["promocode_button"] = lambda: button_html

        return app
