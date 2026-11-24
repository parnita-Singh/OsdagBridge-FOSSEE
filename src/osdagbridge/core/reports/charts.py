"""Charts for the PDF report (utilization ratios and material quantities).

Uses matplotlib's object-oriented API with the Agg canvas, so it never touches
pyplot's global backend (the desktop GUI uses matplotlib with Qt).
Every public function returns a LaTeX snippet and never raises: a chart that
cannot be drawn is skipped, so the report itself is never broken by a chart.
"""
import logging
import os
import re

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from osdagbridge.core.reports.styles import CHART_PASS, CHART_FAIL, CHART_LIMIT, CHART_NEUTRAL

logger = logging.getLogger(__name__)

_NUM = re.compile(r'-?\d+(?:\.\d+)?')

# Which summary-table rows belong to which chart.
UR_GROUPS = [
    ("girder",   "Steel Plate Girders",
     lambda lab: lab.startswith("Girder")),
    ("deck",     "Concrete Deck Slab",
     lambda lab: lab.startswith("Deck") or "(slab)" in lab),
    ("bracing",  "Cross Bracing",
     lambda lab: lab.startswith("Cross Bracing")),
    ("diaphragm", "End Diaphragms",
     lambda lab: lab.startswith("End Diaphragm")),
]


def _to_float(text):
    """First number in a table cell such as '0.87' or '\\textcolor{red}{1.12}'."""
    m = _NUM.search(str(text).replace(r"\textcolor{red}", ""))
    return float(m.group()) if m else None


def _clean_label(label):
    return (str(label).replace(r"\&", "&").replace("---", "-")
            .replace("$", "").replace("\\", "").replace("{", "").replace("}", "").strip())


def _save(fig, path):
    FigureCanvasAgg(fig)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")


def ur_bar_chart(items, title, path):
    """Horizontal bars of UR = demand / capacity with a dashed red limit at 1.0.
    items: [(label, ur)]. Failing bars (UR > 1) are red and hatched, so they
    still stand out in a black-and-white print."""
    n = len(items)
    fig = Figure(figsize=(6.4, max(2.0, 0.42 * n + 1.3)))
    ax = fig.subplots()
    labels = [_clean_label(l) for l, _ in items]
    urs = [u for _, u in items]
    ypos = list(range(n))[::-1]
    for y, u in zip(ypos, urs):
        fail = u > 1.0
        ax.barh(y, u, height=0.6, color=CHART_FAIL if fail else CHART_PASS,
                hatch="///" if fail else None, edgecolor="white" if not fail else "#7a1f14",
                linewidth=0.6)
        ax.text(u + 0.015, y, f"{u:.2f}", va="center", ha="left", fontsize=8,
                color=CHART_FAIL if fail else "#222222",
                fontweight="bold" if fail else "normal",
                bbox=dict(facecolor="white", edgecolor="none", pad=0.6, alpha=0.85))
    ax.axvline(1.0, color=CHART_LIMIT, linestyle="--", linewidth=1.4)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, max(1.15, max(urs) * 1.15))
    ax.set_xlabel("Utilization ratio, UR = Demand / Capacity", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="x", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=CHART_PASS, label="Pass (UR ≤ 1.0)"),
                       Patch(facecolor=CHART_FAIL, hatch="///", edgecolor="#7a1f14", label="Fail (UR > 1.0)"),
                       Line2D([0], [0], color=CHART_LIMIT, linestyle="--", label="Limit, UR = 1.0")],
              fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=3, frameon=False)
    fig.tight_layout()
    _save(fig, path)


def _figure_tex(path, caption, width=r"0.85\textwidth"):
    return (r"\begin{figure}[H]" + "\n" + r"\centering" + "\n"
            + r"\includegraphics[width=" + width + "]{" + path.replace("\\", "/") + "}\n"
            + r"\caption*{" + caption + "}\n" + r"\end{figure}" + "\n")


def build_ur_chart_tex(records, chart_dir):
    """records: [(row label, last table cell)] collected from the summary table."""
    if not chart_dir or not records:
        return ""
    try:
        os.makedirs(chart_dir, exist_ok=True)
        parsed = [(lab, _to_float(cell)) for lab, cell in records]
        parsed = [(lab, ur) for lab, ur in parsed if ur is not None]
        out = [r"\clearpage", r"\subsection*{Utilization Ratio Charts}",
               r"\noindent UR = Demand / Capacity for every check in the table above. "
               r"The dashed red line marks the limit UR = 1.0; bars beyond it fail.", r"\vspace{0.5em}"]
        drawn = 0
        for key, title, belongs in UR_GROUPS:
            items = [(lab, ur) for lab, ur in parsed if belongs(lab)]
            if not items:
                continue
            p = os.path.join(chart_dir, f"ur_{key}.png")
            ur_bar_chart(items, title, p)
            out.append(_figure_tex(p, f"Utilization ratios --- {title}"))
            drawn += 1
        return "\n".join(out) + "\n" if drawn else ""
    except Exception as exc:                      # a chart must never break the report
        logger.warning("UR charts skipped: %s", exc)
        return ""


def _val(input_dict, key):
    try:
        return float(str(input_dict.get(key)).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _bar_panel(ax, labels, values, ylabel, title, color):
    bars = ax.bar(labels, values, color=color, width=0.55)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.tick_params(labelsize=8)
    ax.set_ylim(0, max(values) * 1.18 if max(values) > 0 else 1)
    ax.grid(axis="y", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def build_quantity_chart_tex(input_dict, chart_dir):
    """Steel tonnage (girders, bracing, end diaphragms), concrete volume and
    reinforcement weight, read from the same values as Table 7.1."""
    if not chart_dir:
        return ""
    try:
        os.makedirs(chart_dir, exist_ok=True)
        steel = [("Girders", _val(input_dict, "steel_girders_wt_total")),
                 ("Cross bracing", sum(v for v in (_val(input_dict, k) for k in
                  ("bracing_top_wt_total", "bracing_bot_wt_total", "bracing_diag_wt_total")) if v is not None)
                  if any(_val(input_dict, k) is not None for k in
                  ("bracing_top_wt_total", "bracing_bot_wt_total", "bracing_diag_wt_total")) else None),
                 ("End diaphragms", _val(input_dict, "end_diaphragm_wt_total"))]
        have = [(l, v) for l, v in steel if v is not None]
        out = [r"\subsection*{Material Quantity Charts}"]
        note = ""
        if have:
            fig = Figure(figsize=(5.2, 3.0)); ax = fig.subplots()
            _bar_panel(ax, [l for l, _ in have], [v for _, v in have], "Weight (MT)",
                       "Structural steel (IS 2062), tonnage", CHART_NEUTRAL)
            fig.tight_layout(); p = os.path.join(chart_dir, "qty_steel.png"); _save(fig, p)
            out.append(_figure_tex(p, "Structural steel tonnage by member group", r"0.7\textwidth"))
            if any(v is None for _, v in steel if _ == "End diaphragms"):
                note = "End diaphragm quantity is not computed by the bill of materials, so it is not charted."
        conc, rebar = _val(input_dict, "concrete_deck_vol_total"), _val(input_dict, "rebar_deck_wt_total")
        panels = [("Deck concrete (M40)", conc, "Volume (m\u00b3)"), ("Reinforcement (Fe 500)", rebar, "Weight (MT)")]
        panels = [x for x in panels if x[1] is not None]
        if panels:
            fig = Figure(figsize=(5.6, 2.8)); axes = fig.subplots(1, len(panels), squeeze=False)[0]
            for ax, (name, v, yl) in zip(axes, panels):
                _bar_panel(ax, [name], [v], yl, name, CHART_NEUTRAL)
            fig.tight_layout(); p = os.path.join(chart_dir, "qty_concrete_rebar.png"); _save(fig, p)
            out.append(_figure_tex(p, "Deck concrete volume (m$^3$) and reinforcement steel weight (MT)", r"0.7\textwidth"))
        if len(out) == 1:
            return ""
        if note:
            out.append(r"\noindent\textit{Note: " + note + "}")
        return "\n".join(out) + "\n"
    except Exception as exc:
        logger.warning("Quantity charts skipped: %s", exc)
        return ""