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

Requires a calibration JSON for your PokerTH window resolution in `calibration/` and 52 card templates in `assets/card_templates/`. See `docs/calibration.md` (TODO).

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
