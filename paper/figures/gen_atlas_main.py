"""Single-column, print-sized atlas of System1Bench's historical sources.

The chart is a taxonomy, not an accuracy heatmap. It reads the frozen
``paper/source_atlas.json`` mapping and checks all 15 sources / 28 suites.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "paper" / "source_atlas.json"
if not SOURCE.exists():
    SOURCE = HERE / "source_atlas.json"  # local, read-only rendering stage
OUT = HERE / "fig_atlas_main"

atlas = json.loads(SOURCE.read_text(encoding="utf-8"))
sources = atlas["sources"]
axes = atlas["task_axes"]
suite_ids = [suite for source in sources for suite in source["suites"]]
assert len(sources) == 15 and len(axes) == 8
assert len(suite_ids) == len(set(suite_ids)) == 28
assert {axis["id"] for axis in axes} == {
    "semantic", "routing", "evidence", "ordinal", "safety", "workflow", "rejection", "retrieval"
}
assert all(source["tasks"] and set(source["tasks"]) <= {axis["id"] for axis in axes}
           for source in sources)
assert all(source["reference"] in {"D", "H", "T", "A", "P", "T/P"}
           for source in sources)
assert Counter(source["reference"] for source in sources) == {
    "D": 10, "H": 1, "T": 1, "A": 2, "T/P": 1
}

INK = "#26343E"
MUTED = "#61717A"
NAVY = "#235F7A"
GOLD = "#A8782C"
RULE = "#D9E2E6"
PALE = "#F4F7F8"
DOT = "#D6E0E4"
PAPER = "#FFFFFF"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 9.0,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "figure.facecolor": PAPER,
    "savefig.facecolor": PAPER,
})

fig = plt.figure(figsize=(5.45, 7.75))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

fig.text(.037, .978, "Fifteen sources, eight decision functions",
         ha="left", va="top", color=INK, fontsize=12.2, weight="bold")
fig.text(.038, .946, "Historical suite atlas  ·  28 main suites  ·  function tags overlap",
         ha="left", va="top", color=MUTED, fontsize=8.6)

task_x = [.449 + .0587 * j for j in range(8)]
task_codes = ["SEM", "RTE", "EVD", "ORD", "SFT", "FLW", "REJ", "RET"]
ax.text(.041, .893, "SOURCE / DOMAIN", ha="left", va="center",
        fontsize=8.4, weight="bold", color=INK)
for x, code in zip(task_x, task_codes):
    ax.text(x, .893, code, ha="center", va="center",
            fontsize=8.0, weight="bold", color=INK)
ax.text(.942, .893, "REF", ha="center", va="center",
        fontsize=8.2, weight="bold", color=INK)
ax.plot([.036, .968], [.878, .878], color=INK, lw=.75)

groups = [
    ("LANGUAGE & AFFECT", 0, 3),
    ("SERVICE & ROUTING", 3, 6),
    ("EVIDENCE & INFERENCE", 6, 9),
    ("SAFETY", 9, 11),
    ("WORKFLOW FIXTURES", 11, 15),
]
cursor = .858
row_step = .0360
for title, start, end in groups:
    ax.add_patch(Rectangle((.036, cursor - .014), .932, .020,
                           facecolor=PALE, edgecolor="none", zorder=-2))
    ax.add_patch(Rectangle((.036, cursor - .014), .004, .020,
                           facecolor=NAVY, edgecolor="none", zorder=-1))
    ax.text(.050, cursor - .004, title, ha="left", va="center",
            fontsize=8.15, weight="bold", color=NAVY)
    cursor -= .033
    for source in sources[start:end]:
        y = cursor
        ax.text(.041, y + .008, source["name"], ha="left", va="center",
                fontsize=9.25, weight="medium", color=INK)
        ax.text(.041, y - .011, source["domain"], ha="left", va="center",
                fontsize=8.2, color=MUTED)
        for x, axis in zip(task_x, axes):
            if axis["id"] in source["tasks"]:
                ax.scatter([x], [y], s=52, facecolors=NAVY,
                           edgecolors=PAPER, linewidths=.45, zorder=3)
            else:
                ax.scatter([x], [y], s=12, facecolors=DOT,
                           edgecolors="none", zorder=2)
        ref = source["reference"]
        ax.text(.942, y, ref, ha="center", va="center", fontsize=9.0,
                weight="bold", color=MUTED if ref == "D" else GOLD)
        cursor -= row_step
    cursor -= .005

assert cursor > .09, cursor
ax.plot([.036, .968], [.091, .091], color=RULE, lw=.7)
ax.text(.041, .074,
        "SEM semantic  ·  RTE routing  ·  EVD evidence  ·  ORD ordinal",
        ha="left", va="center", fontsize=8.0, color=MUTED)
ax.text(.041, .055,
        "SFT safety  ·  FLW workflow  ·  REJ rejection  ·  RET retrieval",
        ha="left", va="center", fontsize=8.0, color=MUTED)
ax.text(.041, .034,
        "REF: D dataset  ·  H human  ·  T teacher  ·  A authored  ·  P program",
        ha="left", va="center", fontsize=8.0, color=MUTED)

for ext in ("pdf", "svg", "png"):
    fig.savefig(OUT.with_suffix(f".{ext}"), dpi=360)
plt.close(fig)
print(json.dumps({"source": str(SOURCE),
                  "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  "sources": len(sources), "suites": len(suite_ids),
                  "outputs": [str(OUT.with_suffix(f".{ext}")) for ext in ("pdf", "svg", "png")]},
                 sort_keys=True))
