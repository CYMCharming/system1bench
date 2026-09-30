"""Single-column print figure for the SciFact3 census sensitivity check."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
SUMMARY = HERE / "summary.json"
if not SUMMARY.exists():
    SUMMARY = HERE.parents[1] / "research" / "scifact3_census_v1" / "summary.json"
DATA = json.loads(SUMMARY.read_text(encoding="utf-8"))
OUT = HERE / "fig_scifact3_census_main"

INK = "#22353D"
MUTED = "#61727A"
GRID = "#D9E3E2"
COLORS = {"SUPPORT": "#287F80", "CONTRADICT": "#BD7550", "NOINFO": "#766193", "all": "#334C5A"}
CLASSES = ("SUPPORT", "CONTRADICT", "NOINFO")
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 9.0, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "savefig.facecolor": "white", "figure.facecolor": "white",
})

fig = plt.figure(figsize=(5.42, 3.73))
fig.text(.065, .962, "NoInfo loss survives the balanced-sample selection",
         fontsize=11.25, weight="bold", va="top")
fig.text(.065, .907, "SciFact claim–cited-abstract pairs  ·  Qwen3 8B  ·  joint option reversal",
         fontsize=8.6, color=MUTED, va="top")
fig.text(.065, .842, "REFERENCE MIX", fontsize=8.8, weight="bold")

cohorts = (
    ("prior_selected180", "Selected (180)", 180),
    ("complement159", "Complement (159)", 159),
    ("all339", "Full census (339)", 339),
)
for j, (cohort, name, total) in enumerate(cohorts):
    x0 = .065 + j * .31
    bar_width = .277
    fig.text(x0, .797, name, fontsize=8.55, weight="bold", va="center")
    cursor = x0
    for cls in CLASSES:
        n = DATA["systems"]["qwen3_8b"][cohort][cls]["n"]
        width = bar_width * n / total
        fig.add_artist(Rectangle((cursor, .735), width, .035,
                                 transform=fig.transFigure, facecolor=COLORS[cls],
                                 edgecolor="white", lw=.5))
        if width > .029:
            fig.text(cursor + width / 2, .7525, str(n), ha="center", va="center",
                     fontsize=8.25, color="white", weight="bold")
        else:
            fig.text(cursor + width / 2, .727, str(n), ha="center", va="top",
                     fontsize=8.0, color=COLORS[cls], weight="bold")
        cursor += width
    assert abs(cursor - (x0 + bar_width)) < 1e-10

fig.add_artist(Line2D([.065, .945], [.684, .684], transform=fig.transFigure,
                      color=GRID, lw=.7))
fig.text(.065, .648, "QWEN  /  159-PAIR THREE-CHOICE COMPLEMENT",
         fontsize=8.9, weight="bold", va="center")

ax = fig.add_axes([.267, .185, .568, .390])
ax.set_xlim(0, 100)
ax.set_ylim(-.45, 3.48)
ax.invert_yaxis()
ax.set_xticks([0, 25, 50, 75, 100], labels=["0", "25", "50", "75", "100%"])
ax.set_yticks([0, 1, 2, 3], labels=["Support · 78", "Contradict · 11", "NoInfo · 70", "Overall · 159"])
ax.tick_params(axis="x", labelsize=8.7, length=0, pad=5)
ax.tick_params(axis="y", labelsize=8.65, length=0, pad=7)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.set_axisbelow(True)
ax.grid(axis="x", color=GRID, lw=.65)

for y, cls in enumerate((*CLASSES, "all")):
    cohort = DATA["systems"]["qwen3_8b"]["complement159"][cls]
    n, counts = cohort["n"], cohort["counts"]
    base = 100 * counts["base_correct"] / n
    reverse = 100 * counts["reverse_correct"] / n
    ax.plot([base, reverse], [y, y], color=COLORS[cls], lw=2.5,
            solid_capstyle="round", zorder=3)
    ax.scatter([base], [y], s=55, facecolor="white", edgecolor=COLORS[cls],
               lw=1.8, zorder=4)
    ax.scatter([reverse], [y], s=58, facecolor=COLORS[cls], edgecolor="white",
               lw=.5, zorder=5)
    delta = reverse - base
    fig.text(.86, .534 - y * .099, f"{delta:+.1f}", color=COLORS[cls],
             fontsize=8.9, weight="bold", va="center", ha="left")

fig.text(.86, .588, "Δ pp", fontsize=8.2, color=MUTED)
fig.add_artist(Line2D([.070], [.114], marker="o", markersize=5.5,
                      markerfacecolor="white", markeredgecolor=MUTED,
                      linestyle="None", transform=fig.transFigure))
fig.text(.086, .114, "Original", va="center", fontsize=8.5, color=MUTED)
fig.add_artist(Line2D([.250], [.114], marker="o", markersize=5.5,
                      markerfacecolor=MUTED, markeredgecolor="white",
                      linestyle="None", transform=fig.transFigure))
fig.text(.266, .114, "Reversed", va="center", fontsize=8.5, color=MUTED)
fig.text(.500, .114, "Exact-repeat flips: 0 / 159", va="center",
         fontsize=8.5, color=MUTED)
fig.text(.065, .051, "NoInfo = cited abstract without annotated evidence; not adjudicated neutrality.",
         fontsize=8.15, color=MUTED, va="center")

for ext in ("pdf", "svg", "png"):
    fig.savefig(OUT.with_suffix(f".{ext}"), dpi=360,
                bbox_inches="tight", pad_inches=.04)
plt.close(fig)
