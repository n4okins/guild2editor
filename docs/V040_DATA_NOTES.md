# v0.4 data notes

## Item ordering

The item picker separates presentation order from writable internal IDs.

- Wiki order/grouping is stored in `data/wiki_items.json`.
- Confirmed writable base IDs remain in `data/items.tsv`.
- Names confirmed by the current Wiki but without a confirmed internal ID remain visible as unresolved and are not written to save data.
- Guessed IDs are metadata only and are never used for export until separately confirmed.

For category 1 (細剣), the current Wiki grouping/order is encoded through ノーマル / レア1 / レア2 / ナックル / 投擲. This includes post-v5.10 names such as 大地龍の爪.

## Value ranges

`data/rules.json` contains ranges used by the normal controls:

- level: race-specific cap
- character growth `_p_*`: 0..10
- current four addon allocations: 0..9 each, total <= 23
- rabbit tickets: 0..999
- `adon_time`, `addition_Number`, `premiumTimePoint`: displayed but not edited by normal controls

## Existing save data

A catalog/category disagreement in an already-existing save is a warning, not an export error. The save's existing category is preserved. New item creation uses confirmed catalog category IDs only.
