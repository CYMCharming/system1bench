"""Two-dimensional, source-preserving error complementarity figure.

Reads only the independently checked cross_domain_v1 summary. No suite-level
rates are pooled, and a reference-aware oracle is never called deployable.
"""

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import ROOT, OUT, plt, save  # noqa: E402


summary_path = ROOT / "research/cross_domain_v1/summary.json"
if not summary_path.exists():
    summary_path = HERE / "summary.json"  # portable review copy; remote uses canonical path
summary = json.loads(summary_path.read_text())
assert len(summary["suites"]) == 28
group_order = ["D", "H", "A", "T", "P"]
group_names = {
    "D": "D  DATASET-PROVIDED",
    "H": "H  HUMAN PROMPT",
    "A": "A  AUTHORED / AI-REVIEWED",
    "T": "T  SYNTHETIC TEACHER",
    "P": "P  PROGRAMMATIC",
}
name = {
    "ag_news": "AG News",
    "emotion": "Emotion",
    "banking77": "Banking77",
    "boolq": "BoolQ · noul",
    "boolq_choice": "BoolQ · choice",
    "sst5": "SST-5 · score",
    "sst5_choice": "SST-5 · choice",
    "xnli_en": "XNLI · English",
    "xnli_zh": "XNLI · Chinese",
    "massive_en": "MASSIVE · English",
    "massive_zh": "MASSIVE · Chinese",
    "prompt_injections": "Prompt injections",
    "typed_decisions": "Typed decisions",
    "jevbench_original": "JevBench · original",
    "jevbench_easy": "JevBench · easy",
    "jevbench_hard": "JevBench · hard",
    "reflexbench_reflex-public-choice-v1": "ReflexBench",
    "jev_laya_triage": "Jev–Laya · triage",
    "jev_laya_moderation": "Jev–Laya · moderation",
    "jev_laya_routing": "Jev–Laya · routing",
    "jev_laya_claims": "Jev–Laya · claims",
    "jev_laya_reviews": "Jev–Laya · reviews",
    "jev_laya_guard": "Jev–Laya · guard",
    "jev_laya_multilingual": "Jev–Laya · multilingual",
    "jev_laya_needle": "Jev–Laya · needle",
    "clinc150_oos": "CLINC150 · OOS",
    "turtlebench": "TurtleBench",
    "aegis2_prompt": "Aegis2 prompts",
}
assert set(name) == {x["suite"] for x in summary["suites"]}

ordered = []
for code in group_order:
    group = [x for x in summary["suites"] if x["reference_code"] == code]
    if code == "D":
        # Place related interface variants together; no value sorting.
        desired = [
            "ag_news", "emotion", "banking77", "boolq", "boolq_choice",
            "sst5", "sst5_choice", "xnli_en", "xnli_zh", "massive_en",
            "massive_zh", "clinc150_oos", "turtlebench", "prompt_injections",
        ]
        group = sorted(group, key=lambda x: desired.index(x["suite"]))
    if code == "A":
        desired = ["jevbench_original", "jevbench_easy", "jevbench_hard",
                   "reflexbench_reflex-public-choice-v1"]
        group = sorted(group, key=lambda x: desired.index(x["suite"]))
    ordered.append((code, group))
assert sum(len(group) for _, group in ordered) == 28

fg = "#24333D"
muted = "#596873"
rule = "#D8E1E5"
blue = "#176A8A"
orange = "#C26542"
paper = "#FFFFFF"
fig = plt.figure(figsize=(7.25, 7.3), facecolor=paper)
ax_label = fig.add_axes([.035, .105, .315, .77])
ax_gap = fig.add_axes([.365, .105, .255, .77], sharey=ax_label)
ax_risk = fig.add_axes([.68, .105, .218, .77], sharey=ax_label)
ax_cov = fig.add_axes([.925, .105, .065, .77], sharey=ax_label)
axes = [ax_label, ax_gap, ax_risk, ax_cov]

# Five provenance headings take their own rows; there is deliberately no pooled
# row or all-suite leaderboard at the bottom.
current = 0
headings = []
rows = []
for code, group in ordered:
    headings.append((current, group_names[code]))
    current += 1
    for item in group:
        rows.append((current, item))
        current += 1
total_rows = current
for ax in axes:
    ax.set_ylim(total_rows - .35, -.65)
    ax.spines[:].set_visible(False)
    ax.tick_params(axis="y", left=False, labelleft=False)

ax_label.set_xlim(0, 1)
ax_label.axis("off")
ax_gap.set_xlim(-1.5, 39)
ax_risk.set_xlim(-2, 70)
ax_cov.set_xlim(0, 1)
ax_cov.axis("off")
for ax, ticks in [(ax_gap, [0, 10, 20, 30]), (ax_risk, [0, 20, 40, 60])]:
    ax.set_xticks(ticks, [str(t) for t in ticks])
    ax.tick_params(axis="x", length=2.5, width=.55, pad=4, colors=muted, labelsize=9.0)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#9EADB4")
    ax.spines["bottom"].set_linewidth(.6)
    ax.grid(axis="x", color="#E7ECEE", linewidth=.55, zorder=0)
    ax.set_axisbelow(True)

for y, label in headings:
    for ax in axes:
        ax.axhspan(y - .42, y + .45, facecolor="#F1F5F6", zorder=-1)
    ax_label.text(.005, y + .02, label, ha="left", va="center",
                  fontsize=8.7, weight="bold", color="#42525D")

for y, item in rows:
    ax_label.text(.026, y, name[item["suite"]], ha="left", va="center",
                  color=fg, fontsize=9.35)
    gap = item["oracle_headroom"]
    risk = item["majority_risk"]
    for ax, datum, color in [(ax_gap, gap, blue), (ax_risk, risk, orange)]:
        point = 100 * datum["estimate"]
        lo, hi = [100 * v for v in datum["ci95"]]
        ax.plot([lo, hi], [y, y], color=color, lw=1.55, solid_capstyle="round", zorder=3)
        ax.plot([lo, lo], [y - .085, y + .085], color=color, lw=1.0, zorder=3)
        ax.plot([hi, hi], [y - .085, y + .085], color=color, lw=1.0, zorder=3)
        ax.scatter([point], [y], s=32, color=color, edgecolors=paper, linewidths=.6, zorder=4)
    ax_cov.text(.92, y, f"{100*item['majority_coverage']['estimate']:.0f}%",
                ha="right", va="center", color=muted, fontsize=9.0)

fig.text(.035, .98, "WHEN ERRORS DIVERGE, AGREEMENT CAN STILL MISLEAD",
         ha="left", va="top", color=fg, fontsize=11.5, weight="bold")
fig.text(.035, .938, "28 suites · five systems · pointwise 95% state-cluster intervals",
         ha="left", va="top", color=muted, fontsize=9.0)
fig.text(.365, .892, "ORACLE HEADROOM", ha="left", va="bottom", color=blue, fontsize=8.7, weight="bold")
fig.text(.68, .892, "MAJORITY ERROR RISK", ha="left", va="bottom", color=orange, fontsize=8.7, weight="bold")
fig.text(.925, .892, "COV.", ha="left", va="bottom", color=muted, fontsize=8.7, weight="bold")
fig.text(.365, .077, "Oracle − best single (pp)", ha="left", va="top", color=fg, fontsize=9.0)
fig.text(.68, .077, "Error among covered (%)", ha="left", va="top", color=fg, fontsize=9.0)
fig.text(.035, .025,
         "Oracle = reference-aware upper bound. Majority = ≥3 matching valid labels; risk is conditional on coverage.",
         ha="left", va="top", color=muted, fontsize=8.0)
save(fig, "fig_cross_domain")
