"""Single-column, vector-first generative-baseline figure from verified summary."""

from __future__ import annotations

import json
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter

from style import ROOT, OUT, COLORS, plt


SOURCE = ROOT / "research/strong_baseline_v1/summary.json"
ATLAS = ROOT / "paper/source_atlas.json"
summary = json.loads(SOURCE.read_text())
atlas = json.loads(ATLAS.read_text())
sources = [source["name"] for source in atlas["sources"]]
assert len(sources) == 15
MODELS = ("llama31_8b_instruct", "qwen3_8b")
assert all(set(sources) == set(summary["models"][model]["modes"]["deliberate"]["sources"])
           for model in MODELS)
assert all(summary["models"][model]["modes"][mode]["overall"]["n"] == 212
           for model in MODELS for mode in ("direct", "deliberate"))

INK = "#23333D"
MUTED = "#576770"
FAINT = "#DDE5E8"
ZERO = "#7B898F"
LLAMA = COLORS["llama31_8b_instruct"]
QWEN = COLORS["qwen3_8b"]

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 9.0, "axes.labelsize": 9.0,
    "xtick.labelsize": 8.8, "ytick.labelsize": 8.8,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
})


def signed(value, position=None):
    if abs(value) < 1e-10:
        return "0"
    return f"{value:+.0f}".replace("-", "−")


fig = plt.figure(figsize=(5.4, 7.4), facecolor="white")
fig.text(.045, .975, "SYSTEM1BENCH  /  GENERATIVE CONTROL", fontsize=8.7,
         weight="bold", color=MUTED, va="top")
fig.text(.045, .944, "Prompting changes who is right", fontsize=12.7,
         weight="bold", color=INK, va="top")
fig.text(.045, .909, "Strict one-code parsing  ·  matched cases  ·  no prompt search",
         fontsize=8.8, color=MUTED, va="top")
fig.add_artist(plt.Line2D([.045, .955], [.882, .882], transform=fig.transFigure,
                          color=FAINT, lw=.8))

# The deliberately shallow aggregate chart keeps all four matched conditions
# legible in a true 5.4-inch column. The aligned numbers disclose the flows
# underneath each net accuracy difference.
fig.text(.045, .854, "A  PAIRED OUTCOMES", fontsize=9.1, weight="bold", color=INK)
fig.text(.045, .830, "MODEL / MODE", fontsize=8.6, weight="bold", color=MUTED)
fig.text(.445, .830, "Δ PP · 95% CI", fontsize=8.6, weight="bold", color=MUTED, ha="center")
fig.text(.653, .830, "Δ", fontsize=8.6, weight="bold", color=MUTED, ha="center")
fig.text(.756, .830, "CORRECT", fontsize=8.6, weight="bold", color=MUTED, ha="center")
fig.text(.870, .830, "F / R", fontsize=8.6, weight="bold", color=MUTED, ha="center")
fig.text(.960, .830, "INV", fontsize=8.6, weight="bold", color=MUTED, ha="right")

ax = fig.add_axes([.300, .681, .296, .137])
ax.set_xlim(-9, 12)
ax.set_ylim(-.5, 3.5)
ax.set_xticks([-5, 0, 5, 10])
ax.xaxis.set_major_formatter(FuncFormatter(signed))
ax.grid(axis="x", color=FAINT, lw=.55, zorder=0)
ax.axvline(0, color=ZERO, lw=.85, zorder=1)
ax.set_yticks([3, 2, 1, 0], ["Llama · direct", "Llama · deliberate",
                             "Qwen · direct", "Qwen · deliberate"])
ax.tick_params(axis="y", length=0, pad=7, labelsize=8.9)
ax.tick_params(axis="x", length=2, pad=3, labelsize=8.7)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_color(ZERO)

for model, mode, y in ((MODELS[0], "direct", 3), (MODELS[0], "deliberate", 2),
                       (MODELS[1], "direct", 1), (MODELS[1], "deliberate", 0)):
    block = summary["models"][model]["modes"][mode]
    row = block["overall"]
    low, high = block["overall_ci95_pp"]
    value = row["delta_pp"]
    color = LLAMA if model == MODELS[0] else QWEN
    ax.plot([low, high], [y, y], color=color, lw=1.55, zorder=3,
            solid_capstyle="round")
    ax.plot([low, low], [y-.12, y+.12], color=color, lw=.9, zorder=3)
    ax.plot([high, high], [y-.12, y+.12], color=color, lw=.9, zorder=3)
    ax.scatter(value, y, s=30 if model == MODELS[0] else 28,
               marker="o" if model == MODELS[0] else "D", color=color,
               edgecolor="white", linewidth=.45, zorder=4)
    y_fig = .681 + .137 * (y + .5) / 4
    fig.text(.653, y_fig, f"{value:+.1f}".replace("-", "−") if value else "0.0",
             fontsize=8.9, color=color, ha="center", va="center", weight="bold")
    fig.text(.756, y_fig, f"{row['baseline_correct']}→{row['new_correct']}",
             fontsize=8.9, color=INK, ha="center", va="center")
    fig.text(.870, y_fig, f"{row['corrected']} / {row['regressed']}",
             fontsize=8.9, color=INK, ha="center", va="center")
    fig.text(.960, y_fig, str(row["invalid"]), fontsize=8.9,
             color=INK, ha="right", va="center")

fig.text(.045, .644, "Suite-stratified paired CI; F/R = corrected/regressed; invalids wrong.",
         fontsize=8.5, color=MUTED, va="top")
fig.add_artist(plt.Line2D([.045, .955], [.614, .614], transform=fig.transFigure,
                          color=FAINT, lw=.8))

fig.text(.045, .584, "B  SOURCE HETEROGENEITY", fontsize=9.1, weight="bold", color=INK)
fig.text(.045, .557, "DELIBERATION − CODE-LOGIT · ACCURACY POINTS", fontsize=8.6,
         weight="bold", color=MUTED)
fig.text(.310, .532, "n", fontsize=8.6, weight="bold", color=MUTED, ha="right")
fig.text(.490, .532, "LLAMA 3.1 8B", fontsize=8.9, color=LLAMA,
         weight="bold", ha="center")
fig.text(.816, .532, "QWEN3 8B", fontsize=8.9, color=QWEN,
         weight="bold", ha="center")

bottom, height = .143, .369
names = fig.add_axes([.045, bottom, .275, height])
plots = [fig.add_axes([.353, bottom, .267, height]),
         fig.add_axes([.683, bottom, .267, height])]
for label_ax in (names, *plots):
    label_ax.set_ylim(-.5, 14.5)
    label_ax.set_yticks([])
names.set_xlim(0, 1)
names.set_xticks([])
for spine in names.spines.values():
    spine.set_visible(False)

for index, source in enumerate(sources):
    y = 14 - index
    n = summary["models"][MODELS[0]]["modes"]["deliberate"]["sources"][source]["n"]
    assert n == summary["models"][MODELS[1]]["modes"]["deliberate"]["sources"][source]["n"]
    names.text(0, y, source, fontsize=8.7, color=INK, va="center")
    names.text(.99, y, str(n), fontsize=8.6, color=MUTED, ha="right", va="center")

for plot, model, color, marker in zip(plots, MODELS, (LLAMA, QWEN), ("o", "D")):
    plot.set_xlim(-40, 40)
    plot.set_xticks([-40, 0, 40])
    plot.xaxis.set_major_formatter(FuncFormatter(signed))
    plot.axvline(0, color=ZERO, lw=.9, zorder=1)
    plot.grid(axis="x", color=FAINT, lw=.55, zorder=0)
    plot.tick_params(axis="x", length=2, pad=3, labelsize=8.7)
    plot.spines["left"].set_visible(False)
    plot.spines["bottom"].set_color(ZERO)
    data = summary["models"][model]["modes"]["deliberate"]["sources"]
    for index, source in enumerate(sources):
        y = 14 - index
        effect = data[source]["delta_pp"]
        plot.plot([0, effect], [y, y], color=color, lw=1.55,
                  solid_capstyle="round", zorder=2)
        plot.scatter(effect, y, s=22, marker=marker, color=color,
                     edgecolor="white", linewidth=.4, zorder=3)

fig.text(.045, .093, "Shared ±40 pp scale; source rows are descriptive (n=8–24).",
         fontsize=8.6, color=MUTED, va="top")
fig.text(.045, .067, "Strict parser; post-hoc lenient Qwen parsing is excluded.",
         fontsize=8.6, color=MUTED, va="top")

# Catch later typography regressions before writing a figure used at print size.
fig.canvas.draw()
visible_text = [item for item in fig.findobj(match=Text)
                if item.get_visible() and item.get_text().strip()]
assert min(item.get_fontsize() for item in visible_text) >= 8.5
for extension in ("pdf", "svg", "png"):
    fig.savefig(OUT / f"fig_strong_baseline_main.{extension}", dpi=320)
plt.close(fig)
