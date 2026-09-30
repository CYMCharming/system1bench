"""Single-column, print-size cross-domain error atlas (all 28 frozen suites).

Reads the independently checked cross_domain_v1 summary. It does not average
incommensurate suites or treat the reference-aware oracle as deployable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "research/cross_domain_v1/summary.json"
if not SOURCE.exists():
    SOURCE = HERE / "cross_domain_main_summary.json"  # verified portable review copy
SOURCE_SHA256 = "e98bbf003734705e2b76e385131390d85b2053ab315b6fa36a0dce545bed1e3a"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
DATA = json.loads(SOURCE.read_text(encoding="utf-8"))
assert DATA["analysis"] == "cross-domain-error-complementarity-v1"
assert len(DATA["suites"]) == 28

ORDER = ("D", "H", "A", "T", "P")
GROUPS = {
    "D": "D  DATASET-PROVIDED",
    "H": "H  HUMAN PROMPT",
    "A": "A  AUTHORED / AI-REVIEWED",
    "T": "T  SYNTHETIC TEACHER",
    "P": "P  PROGRAMMATIC",
}
LABELS = {
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
    "clinc150_oos": "CLINC150 · OOS",
    "turtlebench": "TurtleBench",
    "prompt_injections": "Prompt injections",
    "aegis2_prompt": "Aegis2 prompts",
    "jevbench_original": "JevBench · original",
    "jevbench_easy": "JevBench · easy",
    "jevbench_hard": "JevBench · hard",
    "reflexbench_reflex-public-choice-v1": "ReflexBench",
    "typed_decisions": "Typed decisions",
    "jev_laya_triage": "Jev–Laya · triage",
    "jev_laya_moderation": "Jev–Laya · moderation",
    "jev_laya_routing": "Jev–Laya · routing",
    "jev_laya_claims": "Jev–Laya · claims",
    "jev_laya_reviews": "Jev–Laya · reviews",
    "jev_laya_guard": "Jev–Laya · guard",
    "jev_laya_multilingual": "Jev–Laya · multilingual",
    "jev_laya_needle": "Jev–Laya · needle",
}
assert set(LABELS) == {item["suite"] for item in DATA["suites"]}

# Group in reference-provenance order. Within D and A, keep related interface
# variants adjacent; this is not an outcome-selected ordering.
DATASET_ORDER = (
    "ag_news", "emotion", "banking77", "boolq", "boolq_choice", "sst5",
    "sst5_choice", "xnli_en", "xnli_zh", "massive_en", "massive_zh",
    "clinc150_oos", "turtlebench", "prompt_injections",
)
AUTHORED_ORDER = (
    "jevbench_original", "jevbench_easy", "jevbench_hard",
    "reflexbench_reflex-public-choice-v1",
)
by_code = {code: [item for item in DATA["suites"] if item["reference_code"] == code]
           for code in ORDER}
assert [len(by_code[code]) for code in ORDER] == [14, 1, 4, 8, 1]
by_code["D"].sort(key=lambda item: DATASET_ORDER.index(item["suite"]))
by_code["A"].sort(key=lambda item: AUTHORED_ORDER.index(item["suite"]))
assert [item["suite"] for item in by_code["D"]] == list(DATASET_ORDER)
assert [item["suite"] for item in by_code["A"]] == list(AUTHORED_ORDER)

headings = []
rows = []
cursor = 0
for code in ORDER:
    headings.append((cursor, GROUPS[code]))
    cursor += 1
    for item in by_code[code]:
        rows.append((cursor, item))
        cursor += 1
assert cursor == 33 and len(rows) == 28

INK = "#24333D"
MUTED = "#52636C"
BLUE = "#176A8A"
RUST = "#C26542"
RULE = "#D9E2E5"
BAND = "#EFF4F5"
WHITE = "#FFFFFF"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8.6, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "figure.facecolor": WHITE,
    "savefig.facecolor": WHITE, "axes.edgecolor": MUTED,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
})

# Native 5.40-inch width. All authored type is 8.5 pt or larger; the 33-row
# atlas uses a taller aspect ratio instead of shrinking type at paper width.
fig = plt.figure(figsize=(5.40, 8.15), facecolor=WHITE)
bottom, height = .145, .690
ax_label = fig.add_axes([.025, bottom, .326, height])
ax_gap = fig.add_axes([.376, bottom, .215, height], sharey=ax_label)
ax_risk = fig.add_axes([.625, bottom, .215, height], sharey=ax_label)
ax_cov = fig.add_axes([.866, bottom, .109, height], sharey=ax_label)
axes = (ax_label, ax_gap, ax_risk, ax_cov)

for ax in axes:
    ax.set_ylim(cursor - .35, -.65)
    ax.spines[:].set_visible(False)
    ax.tick_params(axis="y", left=False, labelleft=False)
    ax.set_yticks([])
ax_label.set_xlim(0, 1)
ax_label.axis("off")
ax_gap.set_xlim(-1.5, 39)
ax_risk.set_xlim(-2, 70)
ax_cov.set_xlim(0, 1)
ax_cov.axis("off")

for ax, ticks in ((ax_gap, (0, 15, 30)), (ax_risk, (0, 30, 60))):
    ax.set_xticks(ticks, [str(tick) for tick in ticks])
    ax.tick_params(axis="x", length=2.3, width=.55, pad=3.5,
                   colors=MUTED, labelsize=8.5)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#9AAAB1")
    ax.spines["bottom"].set_linewidth(.6)
    ax.grid(axis="x", color="#E8EDEF", linewidth=.55, zorder=0)
    ax.set_axisbelow(True)

for y, heading in headings:
    # A continuous full-width band gives long provenance names their own row,
    # clear of grid lines and data marks, even at native 5.4-inch width.
    fraction = (y - (cursor - .35)) / (-.65 - (cursor - .35))
    fy = bottom + height * fraction
    half = height * .44 / (cursor + .30)
    fig.add_artist(Rectangle((.025, fy - half), .950, 2 * half,
                             transform=fig.transFigure, facecolor=BAND,
                             edgecolor="none", zorder=10))
    fig.text(.028, fy, heading, ha="left", va="center", fontsize=8.6,
             weight="bold", color="#3F515C", zorder=11)

for y, item in rows:
    ax_label.text(.032, y, LABELS[item["suite"]], ha="left", va="center",
                  fontsize=8.65, color=INK)
    for ax, key, color in ((ax_gap, "oracle_headroom", BLUE),
                           (ax_risk, "majority_risk", RUST)):
        datum = item[key]
        point = 100 * datum["estimate"]
        lo, hi = (100 * value for value in datum["ci95"])
        assert lo - 1e-6 <= point <= hi + 1e-6
        ax.plot((lo, hi), (y, y), color=color, lw=1.15,
                solid_capstyle="round", zorder=3)
        ax.plot((lo, lo), (y - .075, y + .075), color=color, lw=.85, zorder=3)
        ax.plot((hi, hi), (y - .075, y + .075), color=color, lw=.85, zorder=3)
        ax.scatter((point,), (y,), s=19, color=color,
                   edgecolors=WHITE, linewidths=.45, zorder=4)
    coverage = 100 * item["majority_coverage"]["estimate"]
    ax_cov.text(.96, y, f"{coverage:.1f}%", ha="right", va="center",
                color=MUTED, fontsize=8.5)

fig.text(.025, .985, "Complementary errors, fragile consensus",
         ha="left", va="top", color=INK, fontsize=11.1, weight="bold")
fig.text(.025, .952, "28 suites · 5 systems · pointwise 95% state-cluster intervals",
         ha="left", va="top", color=MUTED, fontsize=8.55)
fig.text(.376, .860, "ORACLE − BEST", ha="left", va="bottom",
         color=BLUE, fontsize=8.5, weight="bold")
fig.text(.625, .860, "MAJORITY RISK", ha="left", va="bottom",
         color=RUST, fontsize=8.5, weight="bold")
fig.text(.866, .860, "COV.", ha="left", va="bottom",
         color=MUTED, fontsize=8.5, weight="bold")
fig.text(.376, .111, "Oracle − best (pp)", ha="left", va="top",
         color=INK, fontsize=8.5)
fig.text(.625, .111, "Error if covered (%)", ha="left", va="top",
         color=INK, fontsize=8.5)
fig.text(.025, .064, "Oracle uses each reference: upper bound, not a deployable selector.",
         ha="left", va="top", color=MUTED, fontsize=8.5)
fig.text(.025, .038, "Majority: ≥3 matching valid labels; risk is conditional on coverage.",
         ha="left", va="top", color=MUTED, fontsize=8.5)

for ext in ("pdf", "svg", "png"):
    fig.savefig(HERE / f"fig_cross_domain_main.{ext}", dpi=360)
plt.close(fig)
