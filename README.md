# poker-coach

Live Texas Hold'em coaching assistant. Watches a local PokerTH game via screen capture, reads cards/pot/stacks/actions, and prints live equity, pot odds, EV per action, and a recommended decision with explanation — so you can learn the math and logic of NLHE while you play.

## Stack

- Python 3.12, managed with [uv](https://docs.astral.sh/uv/)
- `treys` — hand evaluator
- `grim` (Hyprland/Wayland) — screenshot
- `hyprctl` — locate the PokerTH window
- `opencv-python` — template matching (cards + dealer/SB/BB pucks)
- `pytesseract` — numeric OCR (pot, stacks, bets)
- `matplotlib` — interactive ROI calibration UI
- `rich` — terminal UI

## Install

```bash
# Arch system deps
sudo pacman -S tesseract tesseract-data-eng pokerth grim

# Python deps
uv sync
```

## First-time setup

1. **Launch PokerTH**, start a single-player game vs bots, set whatever window size you like, deal a hand so cards + blinds are visible. Make sure the PokerTH window is on your active workspace and not occluded — `grim` only captures what's on screen.

2. **Calibrate ROIs** (one-shot, robust to later window resizes since coords are anchored to the window center):

   ```bash
   uv run python scripts/calibrate.py --villains 9 --top-sample v3
   ```

   Three phases:
   - *Phase 1* — full window screenshot, you draw the bounding rect for hero + 9 villains + 5 board cards + pot (12 rectangles).
   - *Phase 2* — hero rect is cropped/zoomed, you draw the 6 sub-ROIs (stack, current_bet, cards[0..1], action_label, chip_marker) for the **bottom** layout.
   - *Phase 3* — same inside a top-row villain (default `v3`) for the **top** layout.

   Output: `calibration/pokerth.json`. PokerTH card and puck templates are already in `assets/`.

3. **Verify** what poker-coach sees:

   ```bash
   uv run python scripts/debug_capture.py
   # → annotated PNG at /tmp/poker_coach_debug/annotated.png
   ```

   Each seat row shows its detected stack/bet/chip role (D/SB/BB)/in_hand. Hero row shows recognised cards. If anything is wrong, recalibrate just that ROI:

   ```bash
   uv run python scripts/calibrate.py --only "seats.v2,pot"
   ```

## Run

One-shot — read the table state once and print the advice:

```bash
uv run poker-coach --once
```

Continuous loop (re-parses every 0.5 s and updates when the state changes):

```bash
uv run poker-coach
```

## Reading the TUI

The panel looks like this:

```
┌──────────────────────────────────────────────────────────┐
│ Hero        │ As Qs  (UTG)                               │
│ Board       │ Td 9s 2c  (flop)                           │
│ Pot / Eff   │ $100 / $260                                │
│ To call     │ $40                                        │
│ Hero stack  │ $4860  (SPR 18.7)                          │
│ Active vs   │ 4                                          │
│ Equity      │ 38.2%                                      │
│ Pot odds    │ 13.3%  (need)                              │
│ EV fold     │ +0.0                                       │
│ EV call     │ +75.3                                      │
│ EV raise    │ +148.6                                     │
│ DECISION    │ RAISE                                      │
└──────────────────────────────────────────────────────────┘
```

What each row means and how to act on it:

| Field        | What it is | How to read it |
|--------------|-----------|----------------|
| **Hero**     | Your hole cards + your detected position. | Position matters: same hand plays differently UTG vs BTN. |
| **Board**    | Community cards + current street. | Drives equity. Wet boards (flush/straight draws) help drawing hands; dry boards favour made hands. |
| **Pot / Eff** | `Pot` = chips already swept into the middle. `Eff` (effective pot) = pot + everyone's current-street bets + your own current bet. | **Use `Eff` for all decisions.** It's what you're actually fighting for. |
| **To call**  | Extra chips you must add to stay in the hand. | If 0, you can check for free. Otherwise the price of seeing the next card. |
| **Hero stack** | Chips you have left + SPR (stack-to-pot ratio = `hero_stack / Eff`). | SPR < 3: committed; raises usually mean all-in.  SPR 3–10: standard. SPR > 10: deep, lots of room to play postflop. |
| **Active vs** | Number of villains still in the hand. | Equity drops fast multi-way. AQ heads-up = 64%; AQ vs 6 villains = ~22%. |
| **Equity**   | % chance you win at showdown if all cards are dealt out. Computed by Monte Carlo: 5000 simulations, each villain sampled from their estimated range (open/cold-call/limp depending on their action and position). | This is your *raw winning probability*. Compare with pot odds. |
| **Pot odds (need)** | Break-even equity for a call: `to_call / (Eff + to_call)`. | If `Equity ≥ Pot odds`, calling is at least break-even in pure math. |
| **EV fold**  | Always `+0`. Reference point. | You give up the pot but lose nothing. |
| **EV call**  | Expected chip outcome of calling: `Equity × Eff − (1−Equity) × to_call`. | Positive = profitable long-term. Negative = leak. |
| **EV raise** | Expected chip outcome of raising (sizing shown in parentheses). Accounts for fold equity (probability ALL active villains fold) plus equity if called. | Higher than EV call ⇒ raise is the better line. |
| **DECISION** | Whichever action has the highest EV (CHECK preferred over FOLD when free). | The coach's vote. *You* still decide; use the numbers as a sanity check. |

### Quick decision heuristics

- `Equity` ≥ `Pot odds` → **at minimum CALL**. The gap is your edge per unit invested.
- `EV raise` > `EV call` AND fold equity decent → **RAISE**. Especially on bluff-catcher boards where you can fold worse out.
- `Equity` < `Pot odds` AND `EV raise` ≤ 0 → **FOLD**. Bleeding chips to chase is the #1 leak.
- Multi-way (Active ≥ 4) with a marginal hand: discount equity mentally — even if call is +EV by a tiny margin, variance + reverse-implied odds eat the edge.
- High SPR + drawing hand: don't size up huge calls; you'll lose stack quickly if you hit nothing.
- Low SPR + made hand: the math is mostly already done — get it in.

### Why the coach sometimes says FOLD on a "premium" hand

Heads-up intuition lies in multi-way pots:

- AQs **heads-up** ≈ 64% equity vs random → almost always a call/raise.
- AQs **vs 6 villains** ≈ 22% equity → marginal even with no raises in front.
- AQs **vs an UTG raiser + 3 cold-callers** → callers' ranges still include some AK/sets/Broadways that dominate AQ; equity often drops below pot odds → FOLD is correct.

If the coach says FOLD and you disagree, check **Active vs** and **Equity**. The math doesn't care about feeling.

## Develop

```bash
uv run python -m pytest        # 83 tests
uv run ruff check .
uv run mypy src
```

## Project layout

```
src/poker_coach/
  cards.py         Card / Rank / Suit / Position / Action / Street primitives
  state.py         GameState, Villain, effective_pot
  engine.py        Equity Monte Carlo, pot odds, EV(call/raise)
  ranges.py        Position open ranges + cold-call + limp ranges
  advisor.py       Action-aware range estimation, multi-action EV comparison
  capture.py       grim wrapper
  window.py        hyprctl WindowLocator
  calibration.py   Anchored ROI model (window_center + seat layouts)
  seat_reader.py   Per-seat OCR + chip/card-back detection, position assignment
  ocr.py           Card template matching (multi-scale) + numeric OCR
  parser.py        Glue: capture → seat_reader → GameState
  ui.py            Rich terminal renderer
  main.py          Event loop / --once mode

scripts/
  fetch_pokerth_cards.py   Download 52 card PNGs from upstream PokerTH
  calibrate.py             Interactive ROI calibration (3-phase + --only)
  debug_capture.py         Visualise live capture: annotated PNG + per-ROI prints

assets/
  cards/pokerth/<deck>/    52 card PNGs per deck (default / default4c / default_800x480)
  pokerth/templates/       D/SB/BB pucks + card_back
```

## Disclaimer

For learning against local AI bots in PokerTH only. Do not use against real-money sites — most ToS forbid real-time assistants.

## License

MIT
