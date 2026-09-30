"""Print-size vector figure for the SciFact3 2x2 and Qwen NOINFO migration."""

import json

from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from style import ROOT, plt, save

data = json.loads((ROOT / "research/scifact3_codebook_v1/summary.json").read_text())
assert data["version"] == "scifact3-codebook-v1"

INK = "#25363E"
MUTED = "#596A72"
ACCENT = {"llama31_8b_instruct": "#B86342", "qwen3_8b": "#8A5C8E"}
MODES = (("base", "code_only"), ("display_only", "both"))
MODEL_PANELS = (("llama31_8b_instruct", "Llama 3.1 8B", .015),
                ("qwen3_8b", "Qwen3 8B", .515))
CLASSES = (("NOINFO", "#446D7A"), ("SUPPORT", "#4F9B89"),
           ("CONTRADICT", "#C2704B"))


def shade(accuracy):
    low, high = to_rgb("#F2F5F3"), to_rgb("#A8CFCA")
    level = max(0, min(1, (accuracy - 25) / 45))
    return tuple(low[i] * (1 - level) + high[i] * level for i in range(3))


fig = plt.figure(figsize=(5.35, 4.56), facecolor="white")
fig.text(.018, .974, "The joint reversal is not the sum of its parts",
         fontsize=11.7, weight="bold", color=INK, va="top")
fig.text(.018, .925, "180 matched SciFact3 cited-abstract pairs/model  ·  common semantic tie-break",
         fontsize=9.2, color=MUTED, va="top")

for model, name, offset in MODEL_PANELS:
    info = data["models"][model]["common_tie"]
    fig.text(offset, .865, name, fontsize=10.7, weight="bold", color=ACCENT[model], va="top")
    fig.add_artist(plt.Line2D([offset, offset + .47], [.817, .817],
                              transform=fig.transFigure, color=ACCENT[model], lw=1.3))
    for column, label in ((0, "BASE MAP"), (1, "SWAP MAP")):
        x = offset + .107 + column * .188
        fig.text(x + .085, .787, label, fontsize=9.0, color=MUTED,
                 weight="bold", ha="center", va="center")
    for row, row_label in ((0, "Orig."), (1, "Rev.")):
        y = .625 - row * .17
        fig.text(offset + .003, y + .066, row_label, fontsize=9.2,
                 color=MUTED, va="center", ha="left")
        for column, mode in enumerate(MODES[row]):
            x = offset + .107 + column * .188
            cell = info["cells"][mode]
            assert cell["n"] == 180 and cell["invalid"] == 0
            fig.add_artist(Rectangle((x, y), .17, .133, transform=fig.transFigure,
                                     facecolor=shade(cell["accuracy_percent"]),
                                     edgecolor="#D4DFDF", linewidth=.65))
            fig.text(x + .085, y + .087, f"{cell['accuracy_percent']:.1f}%",
                     fontsize=12.7, weight="bold", color=INK,
                     ha="center", va="center")
            flips = (0 if mode == "base" else
                     info["comparisons"][f"base_to_{mode}"]["prediction_flips"])
            fig.text(x + .085, y + .027, "BASE" if mode == "base" else f"{flips} flips",
                     fontsize=9.0, weight="bold", color=MUTED,
                     ha="center", va="center")

fig.add_artist(plt.Line2D([.018, .98], [.416, .416], transform=fig.transFigure,
                          color="#D7E1E2", lw=.7))
fig.text(.018, .394, "QWEN  /  DESTINATION OF THE SAME 107 BASE-NOINFO PREDICTIONS",
         fontsize=9.2, color=INK, weight="bold", va="top")

qwen = data["models"]["qwen3_8b"]["common_tie"]
transition = qwen["predicted_class_transitions_from_base"]
bar_left, bar_width = .20, .765
for index, (mode, label) in enumerate((("base", "Base"),
                                       ("display_only", "Display"),
                                       ("code_only", "Code"), ("both", "Both"))):
    y = .320 - index * .065
    counts = {"NOINFO": 107} if mode == "base" else transition[mode]["NOINFO"]
    assert sum(counts.values()) == 107
    fig.text(.018, y + .018, label, fontsize=9.2, color=INK, va="center")
    cursor = bar_left
    for cls, color in CLASSES:
        count = counts.get(cls, 0)
        if not count:
            continue
        width = bar_width * count / 107
        fig.add_artist(Rectangle((cursor, y), width, .038,
                                 transform=fig.transFigure, facecolor=color,
                                 edgecolor="white", linewidth=.55))
        if count >= 8:
            fig.text(cursor + width/2, y + .019, str(count),
                     fontsize=8.8, weight="bold", color="white",
                     ha="center", va="center")
        cursor += width

for index, (cls, color) in enumerate(CLASSES):
    x = .21 + index * .247
    fig.add_artist(Rectangle((x, .046), .024, .017,
                             transform=fig.transFigure, facecolor=color, edgecolor="none"))
    fig.text(x + .032, .054, cls, fontsize=8.8, color=MUTED, va="center")

save(fig, "fig_scifact3_codebook")
