#!/usr/bin/env bash
# ClueChain Puzzle Progress Dashboard
# Shows coverage across all 366 calendar days (one puzzle per day)

INDEX="assets/data/indexes/daily.json"
GOAL=366

if [ ! -f "$INDEX" ]; then
  echo "Error: $INDEX not found. Run from the ClueChain project root."
  exit 1
fi

python3 - <<'PYEOF'
import json, calendar

with open("assets/data/indexes/daily.json") as f:
    data = json.load(f)

days = set(data.get("generic_days", []))
total = len(days)
GOAL  = 366

# ANSI colours
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

BAR_WIDTH = 20

def bar(count, total, width=BAR_WIDTH):
    filled = round(count / total * width) if total else 0
    empty  = width - filled
    if count == total:
        colour = GREEN
    elif count >= total * 0.5:
        colour = YELLOW
    else:
        colour = RED
    return f"{colour}{'█' * filled}{'░' * empty}{RESET}"

def status(count, total):
    if count == total:
        return f"{GREEN}✓ complete{RESET}"
    return f"{RED}{total - count} missing{RESET}"

# Days per month (including Feb 29 for the full 366)
MONTH_DAYS = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

pct = total / GOAL * 100

print()
print(f"{BOLD}{'═' * 60}{RESET}")
print(f"{BOLD}  ClueChain Puzzle Dashboard  —  {total}/{GOAL} puzzles ({pct:.1f}%){RESET}")
print(f"{BOLD}{'═' * 60}{RESET}")

overall_bar = bar(total, GOAL, width=40)
print(f"\n  Overall  {overall_bar}  {total}/{GOAL}")
print(f"  {DIM}{GOAL - total} puzzles remaining{RESET}\n")

print(f"  {'Month':<6} {'Progress':<{BAR_WIDTH + 2}} {'Count':>7}  Status")
print(f"  {'─'*5} {'─'*BAR_WIDTH} {'─'*7}  {'─'*14}")

for m in range(1, 13):
    month_total = MONTH_DAYS[m - 1]
    count = sum(1 for d in range(1, month_total + 1) if f"{m:02d}{d:02d}" in days)
    b  = bar(count, month_total)
    st = status(count, month_total)
    print(f"  {MONTH_NAMES[m-1]:<5}  {b}  {count:>3}/{month_total}   {st}")

print()
print(f"{BOLD}{'═' * 60}{RESET}")

# Next suggested month
next_month = next(
    (m for m in range(1, 13)
     if sum(1 for d in range(1, MONTH_DAYS[m-1] + 1) if f"{m:02d}{d:02d}" in days) < MONTH_DAYS[m-1]),
    None
)
if next_month:
    cnt = sum(1 for d in range(1, MONTH_DAYS[next_month-1] + 1) if f"{next_month:02d}{d:02d}" in days)
    left = MONTH_DAYS[next_month - 1] - cnt
    print(f"\n  {BOLD}Next up:{RESET} {MONTH_NAMES[next_month-1]}  ({cnt}/{MONTH_DAYS[next_month-1]} days done, {left} to go)")
else:
    print(f"\n  {BOLD}{GREEN}All 366 puzzles complete!{RESET}")

# ── Day-of-month view ────────────────────────────────────────
# For each day 1–31, how many months have that day covered?
# Max possible per day = number of months that actually have that day.
MONTHS_WITH_DAY = {}
for d in range(1, 32):
    # Count months where day d is valid
    possible = sum(1 for m in range(1, 13) if d <= MONTH_DAYS[m - 1])
    covered  = sum(1 for m in range(1, 13) if d <= MONTH_DAYS[m - 1] and f"{m:02d}{d:02d}" in days)
    MONTHS_WITH_DAY[d] = (covered, possible)

print()
print(f"{BOLD}{'─' * 60}{RESET}")
print(f"{BOLD}  By Day-of-Month  (how many months have each day){RESET}")
print(f"{BOLD}{'─' * 60}{RESET}\n")
print(f"  {'Day':<5} {'Progress':<{BAR_WIDTH + 2}} {'Count':>7}  Status")
print(f"  {'─'*4} {'─'*BAR_WIDTH} {'─'*7}  {'─'*14}")

for d in range(1, 32):
    covered, possible = MONTHS_WITH_DAY[d]
    b  = bar(covered, possible)
    st = status(covered, possible)
    print(f"  {d:>3}   {b}  {covered:>3}/{possible}   {st}")

print()
print(f"{BOLD}{'═' * 60}{RESET}")

next_day = next((d for d in range(1, 32) if MONTHS_WITH_DAY[d][0] < MONTHS_WITH_DAY[d][1]), None)
if next_day:
    covered, possible = MONTHS_WITH_DAY[next_day]
    print(f"\n  {BOLD}Next day gap:{RESET} Day {next_day:02d}  ({covered}/{possible} months done, {possible - covered} to go)")

print()
PYEOF
