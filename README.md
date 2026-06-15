# poker-coach

Live Texas Hold'em coaching assistant. Watches a local PokerTH game via screen capture, reads cards/pot/stacks with OCR, and prints live equity, pot odds, EV per action, and a recommended decision with explanation — so you can learn the math and logic of NLHE while you play.

## Status

Early WIP. Built incrementally:

1. Card/state primitives + poker engine (equity, pot odds, EV)
2. Screen capture + card template matching + numeric OCR
3. Game-state parser, range model, advisor
4. Terminal UI live loop
5. (later) GUI overlay, vision-LLM fallback

## Stack

- Python 3.12, managed with [uv](https://docs.astral.sh/uv/)
- `treys` — fast hand evaluator
- `mss` + `opencv-python` — screen capture and template matching
- `pytesseract` — numeric OCR (pot, stacks)
- `rich` — terminal UI
- `pytest`, `ruff`, `mypy` — quality

## Install

```bash
# system deps (Arch)
sudo pacman -S tesseract tesseract-data-eng pokerth

# project
uv sync
```

## Run

```bash
uv run poker-coach
```

Requires a calibration JSON for your PokerTH window resolution in `calibration/` and 52 card templates in `assets/cards/pokerth/default/` (run `uv run python scripts/fetch_pokerth_cards.py` to download them from upstream PokerTH). See `docs/calibration.md` (TODO).

## TODO — next steps to make it actually run

These are not done yet. Pick up here:

### 1. Install system deps
```bash
sudo pacman -S tesseract tesseract-data-eng pokerth
uv sync
uv run python -m pytest   # 76 tests pass
```

### 2. Launch PokerTH and take a reference screenshot
- Start PokerTH, create a local game vs AI bots (max difficulty).
- Set a fixed window size you'll reuse (e.g. 1920×1080 fullscreen).
- Take a screenshot showing: hero cards visible, full board area, pot label, hero stack label, each villain seat, and the action buttons. Save it to `assets/screenshots/reference_1920x1080.png` (gitignored).

### 3. Download the 52 card templates
PokerTH is GPL and ships its card assets on GitHub. One-liner:
```bash
uv run python scripts/fetch_pokerth_cards.py
```
Pulls 3 decks (`default`, `default4c`, `default_800x480`) into `assets/cards/pokerth/<deck>/`, renaming each PNG to `<RankSuit>.png` (e.g. `As.png`, `Td.png`). Source: https://github.com/pokerth/pokerth/tree/stable/data/gfx/cards.

### 4. Implement `scripts/calibrate.py`
Currently a stub. Needs:
- Load reference screenshot.
- For each named ROI (`hero_cards[0]`, `hero_cards[1]`, `board[0..4]`, `pot`, `hero_stack`, `to_call`, each `villains[i].stack`), let user click top-left + bottom-right with matplotlib `RectangleSelector` (or just `ginput`).
- Write `calibration/pokerth_<W>x<H>.json` matching the schema in `src/poker_coach/calibration.py` (`Calibration.load`).

### 5. First end-to-end smoke test
```bash
uv run poker-coach --calibration calibration/pokerth_1920x1080.json
```
Expected: launches, captures screen, prints a `rich` panel with hero cards, equity, pot odds, EV, decision. If OCR misreads, tune `_MATCH_THRESHOLD` in `src/poker_coach/ocr.py` and tesseract `--psm` config.

### 6. Iterate on the advisor
- Detect betting action from the buttons area to fill `gs.to_call` and `gs.villains[i].last_bet` reliably.
- Narrow villain ranges post-flop based on aggression (currently V1: positional open-range only).
- Add raise sizing recommendation + EV(raise) (needs fold-equity estimate).

### 7. Push to GitHub
```bash
gh repo create poker-coach --private --source=. --remote=origin
git push -u origin main
```

### 8. Later — nice-to-haves
- Transparent GUI overlay over PokerTH (PyQt or `tkinter` `-alpha`).
- Vision LLM fallback for card reading if template matching fails (Anthropic / OpenAI vision).
- Hand history logger + post-session review mode.
- Equity graph (street-by-street).

## Develop

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

## Disclaimer

For learning against local AI bots in PokerTH only. Do not use against real-money sites — most ToS forbid real-time assistants.

## License

MIT
