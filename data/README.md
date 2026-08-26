# Editor data

- `items.tsv`: confirmed writable base item IDs.
- `items_unresolved.tsv`: names observed in current references without confirmed writable IDs.
- `wiki_items.json`: display grouping/order and selected effect metadata.
- `title_order.json`: reference display order for normal/ultra titles.
- `rules.json`: validated UI ranges and read-only fields.
- `catalog.json`: jobs, races, personalities, title names and category names.

Presentation metadata never promotes a guessed item ID into a writable ID. Only confirmed rows from `items.tsv` are used for new item creation.
