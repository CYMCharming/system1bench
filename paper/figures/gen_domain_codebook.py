"""Print-ready orthogonal ContractNLI codebook diagnostic from audited results."""

import json

from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from style import ROOT, plt, save

path = ROOT / "research/domain_codebook_v1/summary_batch4.json"
data = json.loads(path.read_text())
assert data["version"] == "domain-codebook-v1-batch4-correction"
assert all(model["cases"] == 144 and model["document_groups"] == 91
           for model in data["models"].values())

INK = "#23343C"
MUTED = "#607079"
BORDER = "#D8E2E2"
ACCENT = {"llama31_8b_instruct": "#B86342", "qwen3_8b": "#8A5C8E"}
NAMES = {"llama31_8b_instruct": "Llama 3.1 8B", "qwen3_8b": "Qwen3 8B"}
ORDER = (("base", "code_only"), ("display_only", "both"))


def shade(accuracy: float):
    low = to_rgb("#F2F5F3")
    high = to_rgb("#A9CDCB")
    fraction = max(0, min(1, (accuracy - 25) / 40))
    return tuple(low[i] * (1 - fraction) + high[i] * fraction for i in range(3))


def panel(ax, model: str):
    summary = data["models"][model]["common_tie"]
    cells = summary["cells"]
    comparisons = summary["comparisons"]
    ax.set_xlim(0, 4.6)
    ax.set_ylim(0, 3.0)
    ax.axis("off")
    ax.text(0, 2.96, NAMES[model], color=ACCENT[model], weight="bold",
            fontsize=11.5, va="bottom")
    ax.plot([0, 4.53], [2.83, 2.83], color=ACCENT[model], lw=1.45,
            solid_capstyle="round")
    for column, label in ((0, "ORIGINAL MAP"), (1, "REVERSED MAP")):
        x = 1.15 + column * 1.67
        ax.text(x + .73, 2.67, label, color=MUTED, weight="bold",
                fontsize=7.1, ha="center", va="center")
    for row, label in ((0, "Original\nlist"), (1, "Reversed\nlist")):
        y = 1.51 - row * 1.20
        ax.text(.08, y + .50, label, color=MUTED, fontsize=8.0,
                ha="left", va="center", linespacing=1.4)
        for column, mode in enumerate(ORDER[row]):
            x = 1.15 + column * 1.67
            cell = cells[mode]
            acc = cell["accuracy_percent"]
            assert cell["n"] == 144 and cell["invalid"] == 0
            rect = Rectangle((x, y), 1.46, 1.02, linewidth=.8,
                             edgecolor=BORDER, facecolor=shade(acc))
            ax.add_patch(rect)
            ax.text(x + .73, y + .69, f"{acc:.1f}%", color=INK,
                    fontsize=14.5, weight="bold", ha="center", va="center")
            ax.text(x + .73, y + .41, f"{cell['correct']} / 144 correct",
                    color=INK, fontsize=8.0, ha="center", va="center")
            if mode == "base":
                small = "REFERENCE"
            else:
                flips = comparisons[f"base_to_{mode}"]["prediction_flips"]
                small = f"{flips} SWITCHES"
            ax.text(x + .73, y + .15, small, color=MUTED,
                    fontsize=7.1, weight="bold", ha="center", va="center")


fig = plt.figure(figsize=(7.25, 3.65), facecolor="white")
fig.text(.032, .965, "CANDIDATE INTERFACE  /  ORTHOGONAL CONTROL",
         color=MUTED, fontsize=8.0, weight="bold", va="top")
fig.text(.032, .914, "The same reversal conceals different adapter responses",
         color=INK, fontsize=13.0, weight="bold", va="top")
fig.text(.032, .857, "144 matched legal cases per model  ·  accuracy and label switches use a common semantic tie-break",
         color=MUTED, fontsize=8.0, va="top")

left = fig.add_axes([.035, .15, .45, .65])
right = fig.add_axes([.525, .15, .45, .65])
panel(left, "llama31_8b_instruct")
panel(right, "qwen3_8b")

fig.add_artist(plt.Line2D([.035, .975], [.115, .115], transform=fig.transFigure,
                          color=BORDER, lw=.8))
fig.text(.035, .078,
         "NATIVE HISTORICAL JOINT: Llama 59/144 correct, 66 switches  ·  Qwen 83/144 correct, 64 switches",
         color=INK, fontsize=7.7, va="center")
fig.text(.035, .042,
         "Grid re-decodes tied top logits with one fixed label priority (post-hoc sensitivity); source outputs are unchanged.",
         color=MUTED, fontsize=7.5, va="center")
save(fig, "fig_domain_codebook")
