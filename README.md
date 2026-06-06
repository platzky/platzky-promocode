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
                "text": "Reveal your discount",
                "color": "#e63946"
            }
        }
    ]
}
```

| Field | Required | Default | Description |
|---|---|---|---|
| `text` | no | `"Reveal Promo Code"` | Button label before reveal — a plain string, or a `{locale: label}` map for per-language labels |
| `color` | no | `"#4caf50"` | Button background (any CSS color literal) |

### Translated button labels

`text` can be a map of locale codes to labels instead of a single string. The label
matching the visitor's active locale is used, falling back to the first entry in the
map when there is no match:

```json
{
    "plugins": [
        {
            "name": "promocode",
            "config": {
                "text": {
                    "en": "Reveal Promo Code",
                    "pl": "Pokaż kod promocyjny",
                    "uk": "Показати промокод"
                }
            }
        }
    ]
}
```

## Usage in blog content

Embed the promo code directly in post content using the shortcode:

```markdown
Get 20% off with code [promocode]SUMMER24[/promocode] — don't miss out!
```

An optional `color` attribute overrides the configured button colour:

```markdown
Grab your [promocode color="#e91e63"]SAVE20[/promocode] before it expires!
```