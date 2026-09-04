# platzky-promocode

A [platzky](https://github.com/platzky/platzky) plugin that adds a click-to-reveal promo code button.

The reveal is a native `<details>` disclosure, so the plugin ships no JavaScript: it works under a strict CSP and is keyboard- and screen-reader-accessible without any script.

## Installation

```sh
pip install platzky_promocode
```

## Configuration

Plugins are configured in platzky's **database**, under a top-level `plugins` object keyed by
plugin name (for the JSON database that is inside `DB.DATA`; the GraphQL and MongoDB backends
store the same structure):

```json
{
    "plugins": {
        "promocode": {
            "is_active": true,
            "allowed_content_types": ["post", "page", "marker_field"],
            "config": {
                "text": "Reveal your discount",
                "color": "#e63946"
            }
        }
    }
}
```

The key (`promocode`) must match the plugin's entry-point name.

| Field | Required | Default | Description |
|---|---|---|---|
| `is_active` | yes | `false` | The plugin is skipped entirely unless this is `true` |
| `allowed_content_types` | yes | `[]` | Content types the plugin may transform. Platzky provides `post`, `page` and `comment`; a host application adds its own (goodmap contributes `marker_field`). Empty means the plugin loads but transforms nothing |
| `config` | no | `{}` | Plugin settings, see below |

`allowed_content_types` is enforced by the engine and intersected with the content types the
plugin accepts, so it can only narrow them, never widen them. This plugin accepts *every*
content type the application knows — a promo code is inert markup, so there is nowhere it is
unsuited to — which means the grant alone decides where it runs, and naming a type here is
the only thing that switches it on.

Name the types your application actually has. A grant naming an unknown type silently does
nothing, and platzky says so at startup:

```
Plugin PromocodePlugin is granted content type 'field', which this application does not
produce; the grant has no effect. Known types: comment, marker_field, page, post
```

On goodmap the marker-field type is called `marker_field`, not `field`.

### Plugin settings (`config`)

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
    "plugins": {
        "promocode": {
            "is_active": true,
            "allowed_content_types": ["post", "page", "marker_field"],
            "config": {
                "text": {
                    "en": "Reveal Promo Code",
                    "pl": "Pokaż kod promocyjny",
                    "uk": "Показати промокод"
                }
            }
        }
    }
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

## Usage in a goodmap point

On a [goodmap](https://github.com/problematy/goodmap) map the same plugin renders the reveal
button inside a marker popup. Give the point a `promocode` field and list it in
`visible_data`; the value is the code itself, or a dict with per-point overrides:

```json
{
    "name": "Habza cafe",
    "position": [51.078, 17.062],
    "promocode": { "code": "HABZASPOT", "color": "green" }
}
```

`allowed_content_types` must include `marker_field` (see the config above). Nothing else is needed:
the shortcode renders the field itself, and goodmap displays that rendering — there is no
bundle to serve and nothing to register on the frontend. The field must be named after the
shortcode (`promocode`), which is how the host knows to route it here.

Add `head` to `allowed_page_sections` as well, so the plugin's stylesheet is injected:

```yaml
plugins:
  promocode:
    is_active: true
    allowed_content_types: ["marker_field"]
    allowed_page_sections: ["head"]
```