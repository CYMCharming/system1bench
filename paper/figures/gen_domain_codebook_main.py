"""Compact print-size vector version of the legal 2x2 codebook result."""

import json

from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from style import ROOT, plt, save

data = json.loads((ROOT / "research/domain_codebook_v1/summary_batch4.json").read_text())
assert data["version"] == "domain-codebook-v1-batch4-correction"

INK = "#25363E"
MUTED = "#586971"
ACCENT = {"llama31_8b_instruct": "#B86342", "qwen3_8b": "#8A5C8E"}
MODELS = (("llama31_8b_instruct", "Llama 3.1 8B", .015),
          ("qwen3_8b", "Qwen3 8B", .515))
MODES = (("base", "code_only"), ("display_only", "both"))


def background(accuracy):
    start = to_rgb("#F1F5F3")
    end = to_rgb("#ACD0CD")
    weight = max(0, min(1, (accuracy - 25) / 40))
    return tuple(start[i] * (1 - weight) + end[i] * weight for i in range(3))


fig = plt.figure(figsize=(5.35, 2.86), facecolor="white")
fig.text(.018, .952, "Order and answer-code mapping have different effects",
         fontsize=11.7, weight="bold", color=INK, va="top")
fig.text(.018, .865, "144 matched ContractNLI pairs/model  ·  fixed semantic tie-break  ·  batch 4",
         fontsize=9.2, color=MUTED, va="top")

for model, name, offset in MODELS:
    info = data["models"][model]["common_tie"]
    fig.text(offset, .794, name, fontsize=10.7, weight="bold", color=ACCENT[model], va="top")
    fig.add_artist(plt.Line2D([offset, offset + .47], [.718, .718],
                              transform=fig.transFigure, color=ACCENT[model], lw=1.3))
    for column, label in ((0, "BASE MAP"), (1, "SWAP MAP")):
        x = offset + .107 + column * .188
        fig.text(x + .085, .673, label, fontsize=9.0, color=MUTED,
                 weight="bold", ha="center", va="center")
    for row, row_label in ((0, "Orig."), (1, "Rev.")):
        y = .430 - row * .255
        fig.text(offset + .003, y + .099, row_label, fontsize=9.2,
                 color=MUTED, va="center", ha="left")
        for column, mode in enumerate(MODES[row]):
            x = offset + .107 + column * .188
            cell = info["cells"][mode]
            assert cell["n"] == 144 and cell["invalid"] == 0
            fig.add_artist(Rectangle((x, y), .17, .20, transform=fig.transFigure,
                                     facecolor=background(cell["accuracy_percent"]),
                                     edgecolor="#D4DFDF", linewidth=.65))
            fig.text(x + .085, y + .131, f"{cell['accuracy_percent']:.1f}%",
                     fontsize=13.2, weight="bold", color=INK,
                     ha="center", va="center")
            flips = (0 if mode == "base" else
                     info["comparisons"][f"base_to_{mode}"]["prediction_flips"])
            second = "BASE" if mode == "base" else f"{flips} flips"
            fig.text(x + .085, y + .051, second, fontsize=9.3,
                     color=MUTED, weight="bold", ha="center", va="center")

fig.text(.018, .065, "Cells show accuracy; flips count changed semantic labels vs each model's base.",
         fontsize=9.0, color=MUTED, va="bottom")
save(fig, "fig_domain_codebook_main")
