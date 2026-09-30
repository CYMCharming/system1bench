"""Vector figure: paired correctness states on independent natural domains."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

MODELS = ["english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0"]
LABEL = {"english": "Laya English", "multilingual": "Laya Multi",
         "llama31_8b_instruct": "Llama 3.1 8B", "qwen3_8b": "Qwen3 8B", "jev-1.13.0": "Jev 1.13"}
PALETTE = {"both_correct": "#244E63", "correction": "#238A7B",
           "regression": "#C66C47", "both_wrong": "#E8EFF1"}
MODEL_COLOR = {"english": "#176A8A", "multilingual": "#3C8F82",
               "llama31_8b_instruct": "#C26542", "qwen3_8b": "#9A628A",
               "jev-1.13.0": "#424C78"}
INK, MUTED, RULE = "#24333D", "#596873", "#D8E1E5"

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
                     "font.size": 8.2, "axes.labelsize": 8.2, "xtick.labelsize": 7.1,
                     "ytick.labelsize": 7.4, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42,
                     "svg.fonttype": "none", "figure.dpi": 160,
                     "axes.edgecolor": "#42505B", "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED})


def segments(record):
    n = record["n"]
    both = record["count_both_correct"]
    correction = record["count_correction"]
    regression = record["count_regression"]
    wrong = n - both - correction - regression
    assert min(both, correction, regression, wrong) >= 0
    return {"both_correct": 100 * both / n, "correction": 100 * correction / n,
            "regression": 100 * regression / n, "both_wrong": 100 * wrong / n}


def draw(source, title, summary, ax, delta_ax, show_labels):
    data = summary["sources"][source]
    y_positions = list(reversed(range(len(MODELS))))
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.65, 4.75)
    ax.set_yticks(y_positions, [LABEL[m] for m in MODELS] if show_labels else [""] * 5)
    ax.tick_params(axis="y", length=0, pad=5)
    ax.set_xticks([0, 50, 100], ["0", "50", "100%"])
    ax.tick_params(axis="x", length=2, pad=3)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_title(title, loc="left", fontsize=10.0, fontweight="bold", pad=13, color=INK)
    ax.text(1, 1.025, f"n = {data['n']}", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=7.3, color=MUTED)
    for y, model in zip(y_positions, MODELS):
        rec = data["systems"][model]
        seg = segments(rec)
        left = 0
        for name in ["both_correct", "correction", "regression", "both_wrong"]:
            width = seg[name]
            ax.barh(y, width, left=left, height=0.51, color=PALETTE[name],
                    edgecolor="white", linewidth=0.6)
            if width >= 8.8:
                ax.text(left + width / 2, y, f"{width:.0f}", ha="center", va="center",
                        color="white" if name != "both_wrong" else INK,
                        fontsize=7.0, fontweight="medium")
            left += width
        assert abs(left - 100) < 1e-8
    delta_ax.set_xlim(-16, 22)
    delta_ax.set_ylim(-0.65, 4.75)
    delta_ax.set_yticks(y_positions, [LABEL[m] for m in MODELS] if show_labels else [""] * 5)
    delta_ax.tick_params(axis="y", length=0, pad=5)
    delta_ax.axvline(0, color="#98A9B0", linewidth=0.85, zorder=0)
    delta_ax.set_xticks([-10, 0, 10, 20], ["−10", "0", "+10", "+20"])
    delta_ax.tick_params(axis="x", length=2, pad=3)
    delta_ax.spines[["top", "right", "left"]].set_visible(False)
    delta_ax.spines["bottom"].set_color(RULE)
    for y, model in zip(y_positions, MODELS):
        rec = data["systems"][model]["accuracy_delta"]
        val = rec["estimate"] * 100
        lo, hi = [v * 100 for v in rec["ci95"]]
        delta_ax.plot([lo, hi], [y, y], color=MODEL_COLOR[model], linewidth=1.4,
                      solid_capstyle="round", zorder=2)
        delta_ax.plot([lo, lo], [y - 0.105, y + 0.105], color=MODEL_COLOR[model], linewidth=0.9)
        delta_ax.plot([hi, hi], [y - 0.105, y + 0.105], color=MODEL_COLOR[model], linewidth=0.9)
        delta_ax.scatter(val, y, s=21, color=MODEL_COLOR[model], edgecolors="white",
                         linewidths=0.5, zorder=3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.summary.read_text())
    assert list(data["sources"]) == ["contractnli", "scifact"]
    assert all(list(data["sources"][s]["systems"]) == MODELS for s in data["sources"])

    fig = plt.figure(figsize=(7.2, 5.85), facecolor="white")
    fig.text(0.075, 0.955, "PAIRED CORRECTNESS  /  INDEPENDENT NATURAL DOMAINS",
             ha="left", va="top", fontsize=10.5, fontweight="bold", color=INK)
    fig.text(0.075, 0.918, "Same source pair · exact repeat · candidate reversal · five fixed model–adapter systems",
             ha="left", va="top", fontsize=7.3, color=MUTED)
    handles = [Patch(facecolor=PALETTE[key], edgecolor=RULE if key == "both_wrong" else "none")
               for key in ["both_correct", "correction", "regression", "both_wrong"]]
    fig.legend(handles, ["Correct both times", "Corrected by reversal", "Regressed by reversal",
                         "Wrong both times"], ncol=4, loc="upper left", bbox_to_anchor=(0.07, 0.889),
               frameon=False, fontsize=7.2, handlelength=1.0, columnspacing=1.25, handletextpad=0.45)

    # Axis placement is fixed to avoid small-font drift between PDF/SVG/PNG renderers.
    top_left = fig.add_axes([0.205, 0.527, 0.315, 0.255])
    top_right = fig.add_axes([0.59, 0.527, 0.315, 0.255])
    bot_left = fig.add_axes([0.205, 0.19, 0.315, 0.245])
    bot_right = fig.add_axes([0.59, 0.19, 0.315, 0.245])
    draw("contractnli", "LEGAL  /  ContractNLI", data, top_left, bot_left, True)
    draw("scifact", "SCIENCE  /  SciFact", data, top_right, bot_right, False)
    fig.text(0.075, 0.467, "REVERSAL ACCURACY CHANGE", ha="left", va="center",
             fontsize=8.4, fontweight="bold", color=INK)
    fig.text(0.368, 0.467, "percentage points · 95% source-cluster interval",
             ha="left", va="center", fontsize=7.25, color=MUTED)
    fig.text(0.075, 0.115,
             "Legal: 144 balanced document–hypothesis pairs (91 contracts). Science: 120 positive-evidence claim–abstract pairs.",
             ha="left", va="center", fontsize=7.0, color=MUTED)
    fig.text(0.075, 0.091,
             "LLM reversal changes display order and answer-code mapping jointly; strict model/interface effect only.",
             ha="left", va="center", fontsize=7.0, color=MUTED)
    fig.text(0.075, 0.067,
             "Exact-repeat flips: 0 for four local systems; Jev legal 2/144, Jev science 0/120. Error/coverage audited separately.",
             ha="left", va="center", fontsize=7.0, color=MUTED)
    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    for ext in ["pdf", "svg", "png"]:
        fig.savefig(args.out_prefix.with_suffix("." + ext), dpi=320, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


if __name__ == "__main__":
    main()
