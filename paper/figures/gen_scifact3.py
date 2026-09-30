"""Print-ready SciFact3 figure: hidden cancellation under Qwen option reversal.

Reads derived, independently checked case-level decisions and summary metrics.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

INK = "#24333D"
MUTED = "#5B6A73"
RULE = "#D8E1E5"
BLUE = "#244E63"
TEAL = "#238A7B"
ORANGE = "#C66C47"
PALE = "#E9F0F2"
WARM = "#F7E8E1"
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")
SHORT = {"SUPPORT": "Support", "CONTRADICT": "Contradict", "NOINFO": "No info"}

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8.2, "axes.labelsize": 8.2, "xtick.labelsize": 7.4,
    "ytick.labelsize": 8.0, "pdf.fonttype": 42, "svg.fonttype": "none",
    "figure.dpi": 170, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
})


def figure_data(summary, case_level, manifest):
    system = summary["systems"]["qwen3_8b"]
    cases = case_level["systems"]["qwen3_8b"]
    assert len(cases) == 180
    assert case_level["frozen_sha256"] == summary["input_hashes"]["frozen_sha256"]
    assert manifest["prepared_sha256"] == case_level["frozen_sha256"]
    transition = {a: {b: 0 for b in LABELS} for a in LABELS}
    for case in cases:
        a = case["prediction"]["base"]
        b = case["prediction"]["reversed_option_order"]
        assert a in LABELS and b in LABELS
        transition[a][b] += 1
    base_marginal = {a: sum(transition[a].values()) for a in LABELS}
    reverse_marginal = {b: sum(transition[a][b] for a in LABELS) for b in LABELS}
    assert base_marginal == system["all"]["predicted_label_counts"]["base"]
    assert reverse_marginal == system["all"]["predicted_label_counts"]["reversed_option_order"]
    counts = system["all"]["counts"]
    assert counts["flip_base_reverse"] == sum(
        transition[a][b] for a in LABELS for b in LABELS if a != b)
    assert counts["n"] == 180 and counts["flip_base_repeat"] == 0
    per_class = {label: {
        "base_correct": system[label]["counts"]["base_correct"],
        "reverse_correct": system[label]["counts"]["reverse_correct"],
        "delta_pp": 100 * system[label]["metrics"]["reverse_accuracy_delta"]["estimate"],
        "delta_ci95_pp": [100 * v for v in system[label]["metrics"]["reverse_accuracy_delta"]["ci95"]],
    } for label in LABELS}
    return {
        "source_frozen_sha256": summary["input_hashes"]["frozen_sha256"],
        "model": "qwen3_8b", "n": 180, "n_per_reference_label": 60,
        "reference_candidate_pairs": manifest["source_profile"]["label_pairs"],
        "per_class": per_class,
        "transition_base_to_reverse": transition,
        "base_prediction_marginal": base_marginal,
        "reverse_prediction_marginal": reverse_marginal,
        "overall_base_correct": counts["base_correct"],
        "overall_reverse_correct": counts["reverse_correct"],
        "overall_delta_pp": 100 * system["all"]["metrics"]["reverse_accuracy_delta"]["estimate"],
        "overall_delta_ci95_pp": [100 * v for v in system["all"]["metrics"]["reverse_accuracy_delta"]["ci95"]],
        "reverse_prediction_flips": counts["flip_base_reverse"],
        "exact_repeat_prediction_flips": counts["flip_base_repeat"],
        "invalid_base": counts["invalid_base"],
        "invalid_reverse": counts["invalid_reverse"],
    }


def panel_correctness(fig, payload):
    ax = fig.add_axes([0.150, 0.322, 0.360, 0.435])
    ax.set_xlim(0, 60)
    ax.set_ylim(-0.45, 2.55)
    ax.set_yticks([2, 1, 0], [SHORT[label] for label in LABELS])
    ax.set_xticks([0, 20, 40, 60], ["0", "20", "40", "60"])
    ax.tick_params(axis="y", length=0, pad=7)
    ax.tick_params(axis="x", length=2.5, pad=3)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.grid(axis="x", color="#E6ECEE", linewidth=0.65)
    ax.set_axisbelow(True)
    for y, label in zip([2, 1, 0], LABELS):
        row = payload["per_class"][label]
        a, b = row["base_correct"], row["reverse_correct"]
        ax.plot([a, b], [y, y], color="#9EAEB5", linewidth=1.6,
                zorder=2, solid_capstyle="round")
        ax.scatter(a, y, s=42, color=BLUE, edgecolors="white", linewidths=0.7, zorder=3)
        ax.scatter(b, y, s=42, color=ORANGE, edgecolors="white", linewidths=0.7, zorder=4)
        fig.text(0.525, 0.676 - (2-y) * 0.145, f"{a} → {b}",
                 ha="left", va="center", fontsize=8.1, color=INK, weight="bold")
    fig.text(0.151, 0.812, "A  Correct decisions by reference label", weight="bold",
             fontsize=9.7, va="bottom", color=INK)
    fig.text(0.151, 0.784, "count out of 60",
             fontsize=7.25, va="bottom", color=MUTED)
    fig.add_artist(plt.Line2D([0.360], [0.794], transform=fig.transFigure,
                              marker="o", markersize=4.2, color=BLUE, linestyle="None"))
    fig.text(0.373, 0.794, "Base", fontsize=7.2, va="center", color=MUTED)
    fig.add_artist(plt.Line2D([0.425], [0.794], transform=fig.transFigure,
                              marker="o", markersize=4.2, color=ORANGE, linestyle="None"))
    fig.text(0.438, 0.794, "Reversed", fontsize=7.2, va="center", color=MUTED)
    fig.text(0.151, 0.287, "Correct / 60", fontsize=7.3, color=MUTED, va="top")


def panel_transition(fig, payload):
    ax = fig.add_axes([0.710, 0.329, 0.240, 0.425])
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.set_aspect("equal")
    ax.axis("off")
    transition = payload["transition_base_to_reverse"]
    for i, a in enumerate(LABELS):
        for j, b in enumerate(LABELS):
            count = transition[a][b]
            x, y = j, 2-i
            color = WARM if a != b and count else PALE
            if count == 0:
                color = "#F5F7F7"
            ax.add_patch(Rectangle((x+0.045, y+0.045), 0.91, 0.91,
                                   facecolor=color, edgecolor="white", linewidth=0.75))
            ax.text(x+0.5, y+0.54, str(count), ha="center", va="center",
                    fontsize=10.3, weight="bold" if count else "normal",
                    color=ORANGE if a != b and count else INK if count else "#9EACB2")
    for i, label in enumerate(LABELS):
        yfig = 0.689 - i * 0.142
        fig.text(0.698, yfig, SHORT[label], ha="right", va="center",
                 fontsize=7.3, color=MUTED)
    for j, label in enumerate(LABELS):
        xfig = 0.750 + j * 0.080
        fig.text(xfig, 0.318, SHORT[label], ha="center", va="top",
                 fontsize=7.0, color=MUTED)
    fig.text(0.665, 0.812, "B  Base → reversed predictions", weight="bold",
             fontsize=9.7, va="bottom", color=INK)
    fig.text(0.665, 0.784, "rows: base  ·  columns: reversed  ·  n = 180",
             fontsize=7.25, va="bottom", color=MUTED)


def draw(payload, prefix):
    fig = plt.figure(figsize=(7.25, 4.15), facecolor="white")
    fig.text(0.055, 0.963, "SCIENTIFIC EVIDENCE  /  THREE-CLASS CONTROL",
             color=MUTED, fontsize=7.7, weight="bold", va="top")
    fig.text(0.055, 0.920, "Stable total accuracy hides a 60-case answer migration",
             color=INK, fontsize=13.0, weight="bold", va="top")
    fig.text(0.055, 0.873, "Qwen3 8B  ·  180 cited claim–abstract pairs  ·  60 references per class",
             color=MUTED, fontsize=8.0, va="top")
    fig.add_artist(plt.Line2D([0.055, 0.945], [0.838, 0.838], transform=fig.transFigure,
                              color=RULE, linewidth=0.8))
    panel_correctness(fig, payload)
    panel_transition(fig, payload)
    fig.add_artist(plt.Line2D([0.055, 0.945], [0.229, 0.229], transform=fig.transFigure,
                              color=RULE, linewidth=0.8))
    delta = payload["overall_delta_pp"]
    lo, hi = payload["overall_delta_ci95_pp"]
    fig.text(0.055, 0.200,
             f"Overall correct: 104 → 101 / 180  ({delta:+.1f} pp; paired 95% CI [{lo:+.1f}, {hi:+.1f}])",
             fontsize=8.3, color=INK, weight="bold", va="top")
    fig.text(0.055, 0.158,
             "60 / 180 reversed predictions changed, all from base NOINFO; exact repeat changed 0 / 180.",
             fontsize=7.6, color=INK, va="top")
    fig.text(0.055, 0.114,
             "NOINFO: explicitly cited paper without annotated abstract evidence (130 candidates, 60 selected).",
             fontsize=7.0, color=MUTED, va="top")
    fig.text(0.055, 0.084,
             "The LLM adapter also changes answer-code mapping on reversal; this is interface sensitivity, not pure semantics.",
             fontsize=7.0, color=MUTED, va="top")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(prefix.with_suffix("." + ext), dpi=320, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def draw_compact(payload, prefix):
    """One-column paper variant; annotations outside marks stay at print size."""
    fig = plt.figure(figsize=(5.52, 3.02), facecolor="white")
    fig.text(0.045, 0.955, "QWEN3 8B  /  180 CITED CLAIM–ABSTRACT PAIRS",
             fontsize=9.4, color=MUTED, weight="bold", va="top")
    fig.text(0.045, 0.900, "Near-flat accuracy, 60 changed semantic answers",
             fontsize=11.5, color=INK, weight="bold", va="top")
    fig.add_artist(plt.Line2D([0.045, 0.955], [0.830, 0.830],
                              transform=fig.transFigure, color=RULE, linewidth=0.8))
    fig.text(0.045, 0.805, "A  Correct / 60 by reference class", fontsize=9.2,
             color=INK, weight="bold", va="top")
    fig.text(0.630, 0.805, "B  Prediction transitions", fontsize=9.2,
             color=INK, weight="bold", va="top")

    ax = fig.add_axes([0.156, 0.326, 0.364, 0.408])
    ax.set_xlim(0, 60)
    ax.set_ylim(-0.44, 2.44)
    ax.set_yticks([2, 1, 0], ["Support", "Contradict", "No info"])
    ax.set_xticks([0, 30, 60], ["0", "30", "60"])
    ax.tick_params(axis="y", length=0, pad=5, labelsize=8.9)
    ax.tick_params(axis="x", length=2, pad=3, labelsize=8.2)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.grid(axis="x", color="#E6ECEE", linewidth=0.6)
    ax.set_axisbelow(True)
    for y, label in zip([2, 1, 0], LABELS):
        a = payload["per_class"][label]["base_correct"]
        b = payload["per_class"][label]["reverse_correct"]
        ax.plot([a, b], [y, y], color="#9EAEB5", linewidth=1.55,
                zorder=2, solid_capstyle="round")
        ax.scatter(a, y, s=40, color=BLUE, edgecolors="white", linewidths=0.6, zorder=3)
        ax.scatter(b, y, s=40, color=ORANGE, edgecolors="white", linewidths=0.6, zorder=4)
        fig.text(0.531, 0.672 - (2-y) * 0.141, f"{a}→{b}",
                 fontsize=9.0, color=INK, weight="bold", va="center")
    fig.add_artist(plt.Line2D([0.235], [0.752], transform=fig.transFigure,
                              marker="o", markersize=4.5, color=BLUE, linestyle="None"))
    fig.text(0.250, 0.752, "base", fontsize=8.3, color=MUTED, va="center")
    fig.add_artist(plt.Line2D([0.320], [0.752], transform=fig.transFigure,
                              marker="o", markersize=4.5, color=ORANGE, linestyle="None"))
    fig.text(0.335, 0.752, "reversed", fontsize=8.3, color=MUTED, va="center")

    matrix = fig.add_axes([0.723, 0.345, 0.219, 0.374])
    matrix.set_xlim(0, 3)
    matrix.set_ylim(0, 3)
    matrix.set_aspect("equal")
    matrix.axis("off")
    for i, a in enumerate(LABELS):
        for j, b in enumerate(LABELS):
            count = payload["transition_base_to_reverse"][a][b]
            x, y = j, 2-i
            color = WARM if a != b and count else PALE if count else "#F5F7F7"
            matrix.add_patch(Rectangle((x+0.045, y+0.045), 0.91, 0.91,
                                       facecolor=color, edgecolor="white", linewidth=0.6))
            matrix.text(x+0.5, y+0.51, str(count), ha="center", va="center",
                        fontsize=10.3, color=ORANGE if a != b and count else
                        INK if count else "#A0ADB3",
                        weight="bold" if count else "normal")
    for i, label in enumerate(("S", "C", "N")):
        fig.text(0.703, 0.658 - i*0.124, label, ha="right", va="center",
                 fontsize=8.6, color=MUTED)
    for j, label in enumerate(("S", "C", "N")):
        fig.text(0.759 + j*0.073, 0.323, label, ha="center", va="top",
                 fontsize=8.6, color=MUTED)
    fig.text(0.825, 0.740, "base → reverse", ha="center", fontsize=8.0,
             color=MUTED, va="center")
    fig.add_artist(plt.Line2D([0.045, 0.955], [0.233, 0.233],
                              transform=fig.transFigure, color=RULE, linewidth=0.8))
    lo, hi = payload["overall_delta_ci95_pp"]
    fig.text(0.045, 0.198,
             f"Total correct 104→101/180; Δ −1.7 pp (paired 95% CI {lo:+.1f} to {hi:+.1f})",
             fontsize=8.8, color=INK, weight="bold", va="top")
    fig.text(0.045, 0.125,
             "60/180 reversal flips vs 0/180 exact-repeat flips. S/C/N: support/contradict/no-info.",
             fontsize=8.2, color=MUTED, va="top")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(prefix.with_suffix("." + ext), dpi=320, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--case-level", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--data-output", type=Path, required=True)
    parser.add_argument("--compact", action="store_true",
                        help="one-column print-size variant")
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    case_level = json.loads(args.case_level.read_text())
    manifest = json.loads(args.manifest.read_text())
    payload = figure_data(summary, case_level, manifest)
    payload["source_summary_sha256"] = hashlib.sha256(args.summary.read_bytes()).hexdigest()
    payload["source_case_level_sha256"] = hashlib.sha256(args.case_level.read_bytes()).hexdigest()
    payload["source_manifest_sha256"] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    args.data_output.parent.mkdir(parents=True, exist_ok=True)
    if args.data_output.exists() or any(args.out_prefix.with_suffix("."+ext).exists()
                                        for ext in ("pdf", "svg", "png")):
        raise FileExistsError("SciFact3 figure output exists: refusing overwrite")
    args.data_output.write_text(json.dumps(payload, indent=2) + "\n")
    (draw_compact if args.compact else draw)(payload, args.out_prefix)


if __name__ == "__main__":
    main()
