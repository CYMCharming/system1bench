"""Print-size, source-backed SciFact3 census figure.

Inputs are counts and model outputs from the saved census summary only; the
figure never reads source text or redefines the reference relation.
"""

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
OUT = HERE / "fig_scifact3_census"

INK = "#23363E"
MUTED = "#60727A"
GRID = "#DDE5E4"
PAPER = "#FFFFFF"
COLORS = {"SUPPORT": "#297F80", "CONTRADICT": "#BC7551", "NOINFO": "#766292", "all": "#344B58"}
LABELS = {"SUPPORT": "Support", "CONTRADICT": "Contradict", "NOINFO": "NoInfo", "all": "Overall"}
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8.5, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "axes.edgecolor": MUTED,
    "text.color": INK, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "figure.facecolor": PAPER, "savefig.facecolor": PAPER,
})

cohorts = [
    ("prior_selected180", "Selected", 180),
    ("complement159", "Additional", 159),
    ("all339", "Full census", 339),
]
rows = ["SUPPORT", "CONTRADICT", "NOINFO", "all"]
order = ["SUPPORT", "CONTRADICT", "NOINFO"]

fig = plt.figure(figsize=(7.18, 4.48))
fig.text(.045, .962, "NoInfo loss persists beyond the selected sample",
         fontsize=13.2, weight="bold", color=INK, va="top")
fig.text(.045, .905,
         "SciFact claim–cited-abstract pairs  ·  Qwen3 8B  ·  fixed code-logit adapter",
         fontsize=8.75, color=MUTED, va="top")

fig.text(.045, .849, "REFERENCE MIX", fontsize=8.4, weight="bold", color=INK)
fig.text(.045, .823, "Counts shown within each cohort; earlier 180 are deliberately class-balanced.",
         fontsize=7.9, color=MUTED)

for idx, (cohort, title, n) in enumerate(cohorts):
    x0 = .045 + idx * .315
    width = .277
    fig.text(x0, .777, f"{title}  ·  n={n}", fontsize=8.3, weight="bold", va="center")
    cursor = x0
    y = .714
    for cls in order:
        count = DATA["systems"]["qwen3_8b"][cohort][cls]["n"]
        segment = width * count / n
        fig.add_artist(Rectangle((cursor, y), segment, .040,
                                 transform=fig.transFigure, facecolor=COLORS[cls],
                                 edgecolor=PAPER, linewidth=.6))
        if segment >= .040:
            fig.text(cursor + segment / 2, y + .020, f"{count}",
                     ha="center", va="center", fontsize=7.7,
                     weight="bold", color=PAPER)
        else:
            fig.text(cursor + segment / 2, y - .010, f"{count}",
                     ha="center", va="top", fontsize=7.25,
                     weight="bold", color=COLORS[cls])
        cursor += segment
    assert round(cursor - x0, 8) == round(width, 8)

fig.add_artist(Line2D([.045, .963], [.670, .670],
                      transform=fig.transFigure, lw=.65, color=GRID))
for i, (cohort, title, n) in enumerate(cohorts[1:]):
    left = .15 if i == 0 else .605
    ax = fig.add_axes([left, .153, .320, .447])
    ax.set_title(f"{'A' if i == 0 else 'B'}   {title} pairs  ·  n={n}",
                 loc="left", color=INK, fontsize=9.2, weight="bold", pad=12)
    ax.set_xlim(0, 123)
    ax.set_ylim(-.55, 3.65)
    ax.set_xticks([0, 25, 50, 75, 100], labels=["0", "25", "50", "75", "100%"])
    ax.set_yticks(range(4), labels=([f"{LABELS[c]} · {DATA['systems']['qwen3_8b'][cohort][c]['n']}"
                                       for c in rows] if i == 0 else ["", "", "", ""]))
    ax.invert_yaxis()
    ax.tick_params(axis="both", length=0, labelsize=7.55)
    ax.tick_params(axis="y", pad=5)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", color=GRID, lw=.55)
    ax.set_axisbelow(True)
    ax.axvline(100, color=GRID, lw=.65)
    for yi, cls in enumerate(rows):
        counts = DATA["systems"]["qwen3_8b"][cohort][cls]["counts"]
        nr = DATA["systems"]["qwen3_8b"][cohort][cls]["n"]
        assert nr == counts["n"]
        base = counts["base_correct"] / nr * 100
        reverse = counts["reverse_correct"] / nr * 100
        ax.plot([base, reverse], [yi, yi], color=COLORS[cls], lw=2.1,
                solid_capstyle="round", zorder=3)
        ax.scatter([base], [yi], s=48, facecolors=PAPER, edgecolors=COLORS[cls],
                   lw=1.75, zorder=4)
        ax.scatter([reverse], [yi], s=51, facecolors=COLORS[cls], edgecolors=PAPER,
                   lw=.5, zorder=5)
        delta = (counts["reverse_correct"] - counts["base_correct"]) / nr * 100
        ax.text(104, yi, f"{delta:+.1f}", color=COLORS[cls], va="center",
                fontsize=7.55, weight="bold")
    ax.text(.98, 1.035, "Δ pp", transform=ax.transAxes, fontsize=7.3,
            color=MUTED, ha="right")

fig.add_artist(Line2D([.045], [.085], marker="o", markersize=5.7,
                      markerfacecolor=PAPER, markeredgecolor=MUTED,
                      linestyle="None", transform=fig.transFigure))
fig.text(.058, .085, "Original", fontsize=7.9, color=MUTED, va="center")
fig.add_artist(Line2D([.150], [.085], marker="o", markersize=5.7,
                      markerfacecolor=MUTED, markeredgecolor=PAPER,
                      linestyle="None", transform=fig.transFigure))
fig.text(.163, .085, "Reversed options", fontsize=7.9, color=MUTED, va="center")
fig.text(.455, .085, "Exact-repeat label flips: 0 (both cohorts)",
         fontsize=7.9, color=MUTED, va="center")
fig.text(.045, .036,
         "NoInfo = cited abstract without annotated evidence, not adjudicated neutrality; Δ is reversed minus original.",
         fontsize=7.25, color=MUTED, va="center")

for ext in ("pdf", "svg", "png"):
    fig.savefig(OUT.with_suffix(f".{ext}"), dpi=360,
                bbox_inches="tight", pad_inches=.05)
plt.close(fig)
