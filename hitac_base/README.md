# Hitac Base

Branding and cross-cutting overrides for the Hitac ERP.

## What this module owns

Branding that used to be patched directly into `addons/web/` now lives here, so it
travels with the module and the Odoo source tree stays pristine for upstream pulls:

| Thing | Where |
|---|---|
| Brand color `#3b90ca` — navbar background, loading indicator, `$primary` | `static/src/scss/primary_variables.scss` (→ `web._assets_primary_variables`) |
| `.btn-primary` colors (needs its own override; see the file for why) | `static/src/scss/btn_primary.scss` (→ `web.assets_backend`) |
| Navbar sizing (65px tall, 16px font) | `static/src/scss/primary_variables.scss` |
| Browser tab title `Hitac`, favicon | `views/webclient_branding.xml` (inherits `web.layout`) |
| Offline page logo + text | `views/webclient_branding.xml` (inherits `web.webclient_offline`) |
| OdooBot renamed to `Hitac AI` | `data/hitac_bot_data.xml` |
| Logo / favicon assets | `static/img/` |

Installing or updating this module is all that is needed:

```bash
python odoo-bin -c odoo.conf -d <db_name> -u hitac_base --stop-after-init
```

## Module layering

`hitac_base` is the bottom layer: it owns the branding **and every Hitac security group**,
which the other modules' `ir.model.access.csv` files reference. So nothing in `hitac_base`
may depend on another `hitac_*` module:

```
hitac_base
   ^         ^              ^
hitac_supply  hitac_production  (hitac_logistics -> hitac_production)
   ^
hitac_sales
```

This is why `account.move.hitac_supply_order_id` is defined in `hitac_supply` rather than
next to `hitac_sale_order_id` here: its comodel `supply.order` belongs to `hitac_supply`,
and declaring it here would make `hitac_base` depend on `hitac_supply` while
`hitac_supply`'s ACLs already depend on `hitac_base` — a cycle that made clean installs
fail with `No matching record found for external id 'hitac_base.group_hitac_supply_user'`.

## Manual steps on a new instance

These are database records, not code. They are deliberately NOT forced by this module,
because overwriting a live company record on another instance is destructive.

**1. `odoo.conf`** (machine-specific, gitignored):
- `addons_path` must include the `odoo/custom_addons` directory
- keep `limit_time_real = 3600` — the 120s default kills request threads that are merely
  idle on a keep-alive/websocket connection, forcing constant reloads during normal use

**2. Activate Arabic** — Settings → Translations → Languages. The source instance runs
`ar_001` + `en_US`. Without `ar_001` active, the `i18n/ar.po` files in the Hitac modules
never load.

**3. Company settings** (Settings → Companies), as configured on the source instance:
- Name: `Hitac`
- Document layout: `web.external_layout_folder`
- Report footer: `01201179651`
- Primary color: `#0416dc`, Secondary color: `#5061b4`
- A custom report background image is set (`layout_background_image`); re-upload it if the
  PDF layout should match.

Note these report colors are intentionally different from the `#3b90ca` UI brand color —
they style generated PDFs, not the web client.
