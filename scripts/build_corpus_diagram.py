"""Generate docs/diagrams/corpus-units.svg from the processed corpus."""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "firebreak.sqlite"
OUT = ROOT / "docs" / "diagrams" / "corpus-units.svg"

STEP = 14
COLS = 49
R = 3.6
X0 = 48
Y_EXP = 114
Y_CHAR = 360


def _counts() -> dict[str, int]:
    con = sqlite3.connect(DB)
    try:
        base = (
            "FROM experiments WHERE material_class != 'Gas fuel' "
            "AND material != 'unspecified'"
        )
        return {
            "total": con.execute("SELECT count(*) FROM experiments").fetchone()[0],
            "solid": con.execute(f"SELECT count(*) {base}").fetchone()[0],
            "outcomes": con.execute(f"SELECT count(*) {base} AND outcome IS NOT NULL").fetchone()[0],
            "anchors": con.execute(
                f"SELECT count(*) {base} AND gravity = 'microgravity' "
                "AND outcome IS NOT NULL AND pressure_kpa IS NOT NULL"
            ).fetchone()[0],
            "characterisation": con.execute(
                "SELECT count(*) FROM investigation_records"
            ).fetchone()[0],
        }
    finally:
        con.close()


def _positions(count: int, total: int) -> list[int]:
    span = total - 1
    return sorted({round(i * span / (count - 1)) for i in range(count)})


def _grid(count: int, y0: int, cls: str) -> str:
    dots = []
    for i in range(count):
        col, row = i % COLS, i // COLS
        cx = X0 + col * STEP + STEP / 2
        cy = y0 + row * STEP + STEP / 2
        dots.append(f'<circle class="{cls}" cx="{cx}" cy="{cy}" r="{R}"/>')
    return "\n      ".join(dots)


def _overlay(counts: dict[str, int]) -> str:
    solid = _positions(counts["solid"], counts["total"])
    outcomes = [solid[round(i * (len(solid) - 1) / (counts["outcomes"] - 1))]
                for i in range(counts["outcomes"])]
    anchors = outcomes[::2][: counts["anchors"]]

    def circle(i: int, fill: str) -> str:
        col, row = i % COLS, i // COLS
        cx = X0 + col * STEP + STEP / 2
        cy = Y_EXP + row * STEP + STEP / 2
        return f'<circle class="{fill}" cx="{cx}" cy="{cy}" r="{R}"/>'

    parts = [circle(i, "s") for i in solid if i not in outcomes]
    parts += [circle(i, "o") for i in outcomes]
    parts += [
        f'<circle class="ring" cx="{X0 + (i % COLS) * STEP + STEP / 2}" '
        f'cy="{Y_EXP + (i // COLS) * STEP + STEP / 2}" r="{R + 3.4}"/>'
        for i in anchors
    ]
    return "\n      ".join(parts)


def main() -> None:
    c = _counts()
    total_all = c["total"] + c["characterisation"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="550" viewBox="0 0 1200 550" role="img" aria-labelledby="title desc">
  <title id="title">The Firebreak corpus to scale</title>
  <desc id="desc">{total_all:,} curated records drawn as dots. {c["total"]} experiment rows include {c["solid"]} solid-material rows, {c["outcomes"]} documented outcomes and {c["anchors"]} pressure-bearing microgravity anchors. {c["characterisation"]} characterisation rows are labelled and never graded.</desc>
  <style>
    .serif {{ font-family: Georgia, "Times New Roman", serif; }}
    .sans {{ font-family: "Segoe UI", Inter, system-ui, sans-serif; }}
    .mono {{ font-family: Consolas, "Cascadia Mono", "Liberation Mono", monospace; }}
    .r {{ fill: #d6cfc0; }}
    .s {{ fill: #3a3d43; }}
    .o {{ fill: #c2410c; }}
    .c {{ fill: #ded7c8; }}
    .ring {{ fill: none; stroke: #1c1e22; stroke-width: 1.2; }}
  </style>

  <rect width="1200" height="550" fill="#f7f4ec"/>
  <rect x="0.5" y="0.5" width="1199" height="549" fill="none" stroke="#e6e1d5"/>

  <text x="48" y="44" class="mono" font-size="11" fill="#c2410c" letter-spacing="2.2">THE CORPUS, TO SCALE</text>
  <text x="1152" y="44" class="mono" font-size="10" fill="#6f727a" text-anchor="end">{total_all:,} PUBLIC RECORDS · 14 DATASETS</text>
  <text x="48" y="78" class="serif" font-size="19" fill="#2a2c31">{total_all:,} records. Six anchor every grade A.</text>

  <text x="48" y="104" class="mono" font-size="10.5" fill="#5f636b" letter-spacing="1.4">EXPERIMENT ROWS · {c["total"]}</text>
  <g>
      {_grid(c["total"], Y_EXP, "r")}
  </g>
  <g>
      {_overlay(c)}
  </g>

  <line x1="48" y1="322" x2="780" y2="322" stroke="#e6e1d5"/>

  <text x="48" y="348" class="mono" font-size="10.5" fill="#5f636b" letter-spacing="1.4">CHARACTERISATION ROWS · {c["characterisation"]} — LABELLED, NEVER GRADED</text>
  <g>
      {_grid(c["characterisation"], Y_CHAR, "c")}
  </g>

  <line x1="820" y1="114" x2="1152" y2="114" stroke="#e6e1d5"/>
  <text x="820" y="140" class="mono" font-size="10.5" fill="#c2410c" letter-spacing="1.8">WHAT CARRIES EVERY GRADE A</text>
  <text x="820" y="248" class="serif" font-size="104" fill="#c2410c">{c["anchors"]}</text>
  <text x="892" y="200" class="sans" font-size="13.5" fill="#2a2c31">pressure-bearing</text>
  <text x="892" y="219" class="sans" font-size="13.5" fill="#2a2c31">microgravity anchors</text>
  <text x="892" y="238" class="mono" font-size="10.5" fill="#6f727a">in {total_all:,} public records</text>

  <circle class="r" cx="826" cy="296" r="4"/>
  <text x="840" y="300" class="sans" font-size="12.5" fill="#5f636b">experiment row ({c["total"]})</text>
  <circle class="s" cx="826" cy="320" r="4"/>
  <text x="840" y="324" class="sans" font-size="12.5" fill="#5f636b">solid-material row ({c["solid"]})</text>
  <circle class="o" cx="826" cy="344" r="4"/>
  <text x="840" y="348" class="sans" font-size="12.5" fill="#5f636b">documented outcome ({c["outcomes"]})</text>
  <circle class="o" cx="826" cy="368" r="4"/>
  <circle class="ring" cx="826" cy="368" r="7.4"/>
  <text x="840" y="372" class="sans" font-size="12.5" fill="#5f636b">pressure-bearing anchor ({c["anchors"]})</text>

  <text x="820" y="412" class="sans" font-size="12.5" fill="#5f636b">Everything else is a label, a gap, or</text>
  <text x="820" y="431" class="sans" font-size="12.5" fill="#5f636b">evidence capped below grade A.</text>
</svg>
'''
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {c}")


if __name__ == "__main__":
    main()
