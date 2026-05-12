# platzky-promocode

A [platzky](https://github.com/platzky/platzky) plugin that adds a click-to-reveal promo code button.

The promo code is never present as plain text in the page — it is base64-encoded and decoded client-side only on click.

## Installation

```sh
pip install platzky_promocode
```

## Configuration

Register the plugin in your platzky config:

```json
{
    "plugins": [
        {
            "name": "promocode",
            "config": {
                "promo_code": "SUMMER24",
                "text": "Reveal your discount",
                "color": "#e63946"
            }
        }
    ]
}
```

| Field | Required | Default | Description |
|---|---|---|---|
| `promo_code` | yes | — | The code to reveal on click |
| `text` | no | `"Reveal Promo Code"` | Button label before reveal |
| `color` | no | `"#4caf50"` | Button background (any CSS color literal) |

## Usage in a location pin

Add a `promo_code` field to the location data and include it in `visible_data`:

```json
{
    "promo_code": {
        "code": "SUMMER24",
        "text": "Reveal your discount",
        "color": "#e63946"
    }
}
```

When the plugin is enabled, it automatically detects this field and renders it as an interactive button — no extra markup needed in the location data.

## Usage in a Jinja2 template

```html
{{ promocode_button() }}
```

The button uses the `text`, `color`, and `promo_code` values from the plugin config.
