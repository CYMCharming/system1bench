"""Publication vector figure: paired adapter turnover and source heterogeneity."""

import json
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import FuncFormatter

from style import ROOT, COLORS, plt, save

plt.rcParams.update({"xtick.labelsize": 9.0, "ytick.labelsize": 9.0})

summary = json.loads((ROOT / "research/strong_baseline_v1/summary.json").read_text())
atlas = json.loads((ROOT / "paper/source_atlas.json").read_text())
sources = [s["name"] for s in atlas["sources"]]
assert len(sources) == 15
assert set(sources) == set(summary["models"]["qwen3_8b"]["modes"]["deliberate"]["sources"])

MODELS = ["llama31_8b_instruct", "qwen3_8b"]
NAMES = {"llama31_8b_instruct": "Llama 3.1 8B", "qwen3_8b": "Qwen3 8B"}
FIX = "#1C7187"
BREAK = "#C27754"
INK = "#26343D"
GRID = "#E3E9EA"

fig = plt.figure(figsize=(7.25, 6.6), facecolor="white")
outer = GridSpec(2, 1, figure=fig, height_ratios=[1.55, 3.96],
                 left=.245, right=.975, top=.88, bottom=.16, hspace=.33)
top = outer[0].subgridspec(1, 2, width_ratios=[2.8, 1.7], wspace=.06)
ax = fig.add_subplot(top[0])
table = fig.add_subplot(top[1])

rows = [
    ("llama31_8b_instruct", "direct", 3),
    ("llama31_8b_instruct", "deliberate", 2),
    ("qwen3_8b", "direct", 1),
    ("qwen3_8b", "deliberate", 0),
]
for model, mode, y in rows:
    data = summary["models"][model]["modes"][mode]
    outcome = data["overall"]
    n = outcome["n"]
    fix = 100 * outcome["corrected"] / n
    broken = 100 * outcome["regressed"] / n
    delta = outcome["delta_pp"]
    low, high = data["overall_ci95_pp"]
    # The two opposed bars show the two hidden flows behind net accuracy.
    ax.barh(y + .08, fix, left=0, height=.22, color=FIX, edgecolor="none", zorder=3)
    ax.barh(y + .08, broken, left=-broken, height=.22, color=BREAK, edgecolor="none", zorder=3)
    ax.plot([low, high], [y - .19, y - .19], color=COLORS[model], lw=1.25, zorder=4)
    ax.plot([low, low], [y - .25, y - .13], color=COLORS[model], lw=.8, zorder=4)
    ax.plot([high, high], [y - .25, y - .13], color=COLORS[model], lw=.8, zorder=4)
    ax.scatter(delta, y - .19, s=32, marker="D", color=COLORS[model],
               edgecolor="white", linewidth=.45, zorder=5)
    table.text(.07, y, f"{outcome['baseline_correct']}→{outcome['new_correct']}",
               va="center", ha="left", fontsize=8.6, color=INK)
    table.text(.52, y, f"{outcome['corrected']}/{outcome['regressed']}",
               va="center", ha="center", fontsize=8.6, color=INK)
    table.text(.92, y, str(outcome["invalid"]),
               va="center", ha="center", fontsize=8.6, color=INK)

ax.axvline(0, color="#89959B", lw=.8, zorder=1)
ax.axhline(1.5, color="#DCE3E5", lw=.65)
ax.set_yticks([3, 2, 1, 0], ["Llama · direct", "Llama · deliberate",
                             "Qwen · direct", "Qwen · deliberate"])
ax.set_ylim(-.6, 3.62)
ax.set_xlim(-13, 17)
ax.set_xticks([-10, 0, 10])
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:+.0f}" if v else "0"))
ax.grid(axis="x", color=GRID, linewidth=.55, zorder=0)
ax.tick_params(axis="y", length=0, pad=6)
ax.tick_params(axis="x", length=2, pad=3)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_color("#9EAAAF")
table.set_xlim(0, 1)
table.set_ylim(-.6, 3.62)
table.set_xticks([])
table.set_yticks([])
for side in table.spines.values():
    side.set_visible(False)
table.text(.07, 3.59, "RIGHT", fontsize=7.7, weight="bold", color="#6D777C", va="bottom")
table.text(.52, 3.59, "FIX / BREAK", fontsize=7.7, weight="bold", color="#6D777C", ha="center", va="bottom")
table.text(.92, 3.59, "BAD", fontsize=7.7, weight="bold", color="#6D777C", ha="center", va="bottom")

bottom = outer[1].subgridspec(1, 2, wspace=.16)
axes = [fig.add_subplot(bottom[i]) for i in range(2)]
ypos = np.arange(len(sources))[::-1]
for ax2, model in zip(axes, MODELS):
    rows_by_source = summary["models"][model]["modes"]["deliberate"]["sources"]
    for y, source in zip(ypos, sources):
        effect = rows_by_source[source]["delta_pp"]
        ax2.plot([0, effect], [y, y], color=COLORS[model], lw=2.0,
                 alpha=.82, solid_capstyle="round", zorder=2)
        ax2.scatter(effect, y, s=20, facecolor=COLORS[model], edgecolor="white",
                    linewidth=.45, zorder=3)
    ax2.axvline(0, color="#68767D", lw=.8, zorder=1)
    ax2.set_xlim(-43, 43)
    ax2.set_xticks([-40, -20, 0, 20, 40])
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:+.0f}" if v else "0"))
    ax2.grid(axis="x", color=GRID, linewidth=.5, zorder=0)
    ax2.set_ylim(-.7, len(sources) - .3)
    ax2.tick_params(axis="x", length=2, pad=3)
    ax2.tick_params(axis="y", length=0, pad=6)
    ax2.spines["left"].set_visible(False)
    ax2.spines["bottom"].set_color("#9EAAAF")
    ax2.text(0, 1.006, NAMES[model], transform=ax2.transAxes,
             fontsize=10.0, weight="bold", color=COLORS[model], va="bottom")

left = axes[0]
left.set_yticks(ypos, [f"{source}  ·  {summary['models'][MODELS[0]]['modes']['deliberate']['sources'][source]['n']}"
                       for source in sources])
axes[1].set_yticks(ypos, [])
fig.text(.025, .973, "GENERATIVE ADAPTERS", fontsize=8.5, color="#66747C", weight="bold")
fig.text(.025, .941, "Deliberation shifts decisions, not uniformly accuracy",
         fontsize=13.0, weight="bold", color=INK)
fig.text(.245, .900, "PAIRED TRANSITIONS  ·  Δ accuracy vs. code-logit (pp), 212 states / model", fontsize=8.2,
         color="#66747C", weight="bold")
fig.text(.245, .661, "Signed bars: corrected (+) / regressed (−)     ◆ net Δ and 95% paired CI",
         fontsize=8.0, color="#56656D")
fig.text(.245, .632, "SOURCE HETEROGENEITY  ·  deliberate − code-logit (pp)",
         fontsize=8.2, color="#66747C", weight="bold")
fig.text(.245, .082, "Source effects: n=8–24, descriptive only; not separate significance tests.",
         fontsize=7.8, color="#56656D")
fig.text(.245, .057, "Strict parser; invalids wrong. Post-hoc Qwen sensitivity excluded.",
         fontsize=7.8, color="#56656D")
save(fig, "fig_strong_baseline")
