# Card assets source

Downloaded from https://github.com/pokerth/pokerth/tree/stable/data/gfx/cards
via `scripts/fetch_pokerth_cards.py`.

PokerTH is GPL-licensed. Original numeric filenames (`0.png` .. `51.png`) are
renamed to `<rank><suit>.png` (e.g. `As.png`). Mapping:
- `id // 13` = suit (`d, h, s, c`)
- `id % 13`  = rank (`2..9, T, J, Q, K, A`)

Decks: `default`, `default4c` (4-color), `default_800x480` (low-res).
