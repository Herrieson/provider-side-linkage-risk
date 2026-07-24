from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


COLORS = {
    "ink": "#17212B",
    "muted": "#5B6670",
    "blue": "#2878B5",
    "teal": "#2A9D8F",
    "gold": "#D99B2B",
    "red": "#C65353",
    "green": "#4A8F5B",
    "light_blue": "#EAF3FA",
    "light_teal": "#E8F5F2",
    "light_gold": "#FBF2DF",
    "light_red": "#F9EAEA",
    "light_gray": "#F2F4F6",
}


def generate_figures(
    output_dir: Path,
    *,
    selected: tuple[str, ...] = ("all",),
    formats: tuple[str, ...] = ("pdf", "png"),
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    figure_builders = {
        "carp_pipeline": _visual_linkage_overview,
        "evidence_layers": _evidence_layers,
        "t3_longitudinal": _t3_longitudinal,
        "results_overview": _results_overview,
    }
    names = tuple(figure_builders) if "all" in selected else selected
    outputs = []
    for name in names:
        outputs.extend(_save(figure_builders[name](), output_dir / name, formats=formats))
    return outputs


def _carp_pipeline() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.0, 3.94))
    ax.set_xlim(0, 133.33)
    ax.set_ylim(0, 75)
    ax.axis("off")

    def add_box(
        x: float,
        y: float,
        width: float,
        height: float,
        label: str,
        fill: str,
        edge: str,
        *,
        fontsize: float = 7.3,
        linestyle: str = "-",
        fontweight: str = "normal",
    ) -> None:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.25,rounding_size=0.65",
                linewidth=1.1,
                linestyle=linestyle,
                edgecolor=edge,
                facecolor=fill,
            )
        )
        ax.text(
            x + width / 2,
            y + height / 2,
            label,
            ha="center",
            va="center",
            color=COLORS["ink"],
            fontsize=fontsize,
            fontweight=fontweight,
        )

    def add_arrow(
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        color: str = COLORS["muted"],
        connectionstyle: str = "arc3",
    ) -> None:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=7,
                linewidth=0.9,
                color=color,
                connectionstyle=connectionstyle,
            )
        )

    ax.text(
        66.665,
        72.8,
        "Measuring Provider-Side Linkage in LLM Agent Traffic",
        ha="center",
        va="center",
        weight="bold",
        fontsize=10.2,
    )
    ax.text(
        66.665,
        68.9,
        "Protocol identifiers are removed; persistent task objects and replayed state can remain linkable.",
        ha="center",
        va="center",
        color=COLORS["muted"],
        fontsize=7.2,
    )
    ax.text(
        2,
        65.0,
        "CONTROLLED MEASUREMENT",
        ha="left",
        va="center",
        color=COLORS["muted"],
        weight="bold",
        fontsize=7.2,
    )
    add_box(
        2.0,
        53.0,
        12.0,
        8.0,
        "Agent\nrequests",
        COLORS["light_gray"],
        COLORS["ink"],
        fontweight="bold",
    )
    add_box(
        17.5,
        53.0,
        16.5,
        8.0,
        "Broker / gateway\nremove protocol IDs",
        COLORS["light_blue"],
        COLORS["blue"],
        fontsize=6.8,
        fontweight="bold",
    )
    add_box(
        37.5,
        52.0,
        20.0,
        10.0,
        "Provider view\nplaintext content +\nallowed telemetry",
        COLORS["light_teal"],
        COLORS["teal"],
        fontsize=6.8,
        fontweight="bold",
    )
    add_box(
        62.0,
        56.5,
        16.0,
        5.5,
        "Original request",
        "white",
        COLORS["gold"],
        fontweight="bold",
    )
    add_box(
        62.0,
        48.5,
        16.0,
        6.0,
        "Paired control\none channel perturbed",
        COLORS["light_gold"],
        COLORS["gold"],
        fontsize=6.9,
        fontweight="bold",
    )
    add_box(
        82.5,
        52.5,
        14.0,
        8.0,
        "Same method\nCARP or ASL",
        COLORS["light_red"],
        COLORS["red"],
        fontsize=7.0,
        fontweight="bold",
    )
    add_box(
        100.5,
        51.5,
        30.0,
        10.0,
        "Compare linkage scores\nand attribute the channel",
        COLORS["light_gray"],
        COLORS["ink"],
        fontsize=7.2,
        fontweight="bold",
    )
    add_box(
        82.5,
        43.8,
        18.0,
        5.8,
        "Sealed truth\nlabels only; evaluator opens",
        "white",
        COLORS["red"],
        fontsize=6.2,
        linestyle="--",
        fontweight="bold",
    )
    add_arrow((14.3, 57.0), (17.2, 57.0))
    add_arrow((34.3, 57.0), (37.2, 57.0))
    add_arrow((57.8, 57.0), (61.7, 59.1), color=COLORS["gold"])
    add_arrow((57.8, 57.0), (61.7, 51.5), color=COLORS["gold"])
    add_arrow((78.3, 59.1), (82.2, 57.5), color=COLORS["gold"])
    add_arrow((78.3, 51.5), (82.2, 55.5), color=COLORS["gold"])
    add_arrow((96.8, 56.5), (100.2, 56.5))
    add_arrow(
        (100.7, 47.0),
        (115.0, 51.2),
        color=COLORS["red"],
        connectionstyle="arc3,rad=-0.08",
    )

    ax.plot([2.0, 131.0], [41.0, 41.0], color="#C8CFD6", linewidth=0.8)
    ax.text(
        2.0,
        38.8,
        "COMPLEMENTARY BOUNDED LINKAGE METHODS",
        ha="left",
        va="center",
        weight="bold",
        color=COLORS["muted"],
        fontsize=7.2,
    )
    ax.text(
        131.0,
        38.8,
        "same provider-visible requests; no CARP $\\rightarrow$ ASL dependency",
        ha="right",
        va="center",
        color=COLORS["muted"],
        fontsize=6.4,
    )
    add_box(
        2.0,
        30.5,
        10.0,
        5.5,
        "CARP",
        COLORS["light_blue"],
        COLORS["blue"],
        fontsize=8.0,
        fontweight="bold",
    )
    carp_stages = [
        (15.0, "Block +\nindex"),
        (37.0, "Context\ncandidates"),
        (59.0, "Budgeted\nrefinement"),
        (81.0, "Typed-handle\npropagation"),
    ]
    for x, label in carp_stages:
        add_box(
            x,
            30.0,
            18.0,
            6.5,
            label,
            COLORS["light_blue"],
            COLORS["blue"],
            fontsize=7.1,
            fontweight="bold",
        )
    for start, end in ((12.0, 15.0), (33.0, 37.0), (55.0, 59.0), (77.0, 81.0)):
        add_arrow((start + 0.3, 33.25), (end - 0.3, 33.25), color=COLORS["blue"])
    ax.text(
        103.0,
        33.25,
        "Sparse discovery across\nrequests and components",
        ha="left",
        va="center",
        color=COLORS["blue"],
        weight="bold",
        fontsize=6.8,
    )

    add_box(
        2.0,
        22.0,
        10.0,
        5.5,
        "ASL",
        COLORS["light_teal"],
        COLORS["teal"],
        fontsize=8.0,
        fontweight="bold",
    )
    asl_stages = [
        (15.0, "Bounded\nAgent state"),
        (37.0, "Multi-view\ncandidates"),
        (59.0, "Support--conflict\ngate"),
        (81.0, "Selective\nhierarchy"),
    ]
    for x, label in asl_stages:
        add_box(
            x,
            21.5,
            18.0,
            6.5,
            label,
            COLORS["light_teal"],
            COLORS["teal"],
            fontsize=7.1,
            fontweight="bold",
        )
    for start, end in ((12.0, 15.0), (33.0, 37.0), (55.0, 59.0), (77.0, 81.0)):
        add_arrow((start + 0.3, 24.75), (end - 0.3, 24.75), color=COLORS["teal"])
    ax.text(
        103.0,
        24.75,
        "State-aware linkage with\nabstention and conflicts",
        ha="left",
        va="center",
        color=COLORS["teal"],
        weight="bold",
        fontsize=6.8,
    )

    ax.plot([2.0, 131.0], [18.5, 18.5], color="#C8CFD6", linewidth=0.8)
    ax.text(
        2.0,
        16.2,
        "PRIVACY-RELEVANT OUTCOMES",
        ha="left",
        va="center",
        color=COLORS["muted"],
        weight="bold",
        fontsize=7.2,
    )
    outcomes = [
        (2.0, "Workflow partitions", "requests grouped\ninto workflows", COLORS["light_blue"], COLORS["blue"]),
        (34.5, "Cross-workflow entities", "projects, customers,\nor processes", COLORS["light_teal"], COLORS["teal"]),
        (67.0, "Supported partial profiles", "technologies, services,\ndependencies", COLORS["light_gold"], COLORS["gold"]),
        (99.5, "Later-traffic watchlists", "new requests assigned\nto prior components", COLORS["light_red"], COLORS["red"]),
    ]
    for x, title, subtitle, fill, edge in outcomes:
        add_box(x, 3.0, 29.0, 10.5, "", fill, edge)
        ax.text(x + 20.2, 10.4, title, ha="center", va="center", weight="bold", fontsize=6.5)
        ax.text(x + 20.2, 6.4, subtitle, ha="center", va="center", color=COLORS["muted"], fontsize=6.0)

    # Small semantic icons; all meaning remains available in text and line style.
    for x in (6.0, 9.0, 12.0):
        ax.scatter(x, 8.3, s=18, facecolor=COLORS["light_blue"], edgecolor=COLORS["blue"], linewidth=0.8, zorder=4)
    add_arrow((6.7, 8.3), (8.3, 8.3), color=COLORS["blue"])
    add_arrow((9.7, 8.3), (11.3, 8.3), color=COLORS["blue"])
    ax.scatter([38.8, 38.8, 46.0], [9.7, 6.9, 8.3], s=[18, 18, 26], facecolor=COLORS["light_teal"], edgecolor=COLORS["teal"], linewidth=0.8, zorder=4)
    add_arrow((39.6, 9.5), (44.8, 8.5), color=COLORS["teal"])
    add_arrow((39.6, 7.1), (44.8, 8.1), color=COLORS["teal"])
    for y, length in ((10.0, 8.0), (8.2, 6.0), (6.4, 9.0)):
        ax.plot([71.0, 71.0 + length], [y, y], color=COLORS["gold"], linewidth=2.0)
    ax.plot([104.0, 113.0], [7.5, 7.5], color=COLORS["gold"], linewidth=0.9)
    ax.scatter([106.0, 109.5, 112.5], [7.5, 7.5, 7.5], s=20, facecolor="white", edgecolor=[COLORS["blue"], COLORS["teal"], COLORS["red"]], linewidth=0.9, zorder=4)

    fig.tight_layout(pad=0.2)
    return fig


def _visual_linkage_overview() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.0, 3.94))
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 90)
    ax.axis("off")

    def text(
        x: float,
        y: float,
        label: str,
        *,
        size: float = 7.2,
        color: str = COLORS["ink"],
        weight: str = "normal",
        ha: str = "center",
    ) -> None:
        ax.text(x, y, label, ha=ha, va="center", fontsize=size, color=color, weight=weight)

    def box(
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: str = "white",
        edge: str = COLORS["ink"],
        dashed: bool = False,
        radius: float = 1.0,
    ) -> None:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle=f"round,pad=0.15,rounding_size={radius}",
                facecolor=fill,
                edgecolor=edge,
                linewidth=1.05,
                linestyle="--" if dashed else "-",
            )
        )

    def arrow(
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        color: str = COLORS["muted"],
        width: float = 0.9,
        dashed: bool = False,
        connectionstyle: str = "arc3",
    ) -> None:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=7,
                linewidth=width,
                linestyle="--" if dashed else "-",
                color=color,
                connectionstyle=connectionstyle,
            )
        )

    def node(x: float, y: float, *, color: str, kind: str = "circle", size: float = 1.8) -> None:
        if kind == "diamond":
            points = [(x, y + size), (x + size, y), (x, y - size), (x - size, y)]
            ax.add_patch(Polygon(points, closed=True, facecolor="white", edgecolor=color, linewidth=1.0))
        else:
            ax.add_patch(Circle((x, y), size, facecolor="white", edgecolor=color, linewidth=1.0))

    def request_card(x: float, y: float, *, color: str, marker: bool = True) -> None:
        box(x, y, 13.0, 9.0, fill="white", edge=color, radius=0.7)
        for offset, width in ((6.6, 7.2), (4.8, 9.2), (3.0, 5.7)):
            ax.add_patch(Rectangle((x + 1.5, y + offset), width, 0.48, facecolor="#D6DCE2", edgecolor="none"))
        if marker:
            node(x + 10.8, y + 6.8, color=COLORS["gold"], kind="diamond", size=1.05)

    def workflow(x: float, y: float, color: str) -> None:
        for index in range(3):
            node(x + index * 5.0, y, color=color, size=1.25)
            if index < 2:
                arrow((x + 1.4 + index * 5.0, y), (x + 3.6 + index * 5.0, y), color=color, width=0.7)

    text(80, 86.5, "Identifier stripping does not remove content linkage", size=10.0, weight="bold")

    panels = [
        (2.0, "A", "PROTOCOL VIEW", COLORS["blue"]),
        (55.5, "B", "LINKAGE MEASUREMENT", COLORS["teal"]),
        (109.0, "C", "LONGITUDINAL VIEW", COLORS["gold"]),
    ]
    for x, letter, title, color in panels:
        box(x, 3.0, 49.0, 78.0, fill="white", edge="#D6DCE2", radius=1.0)
        ax.add_patch(Circle((x + 4.3, 76.2), 2.25, facecolor=color, edgecolor=color))
        text(x + 4.3, 76.2, letter, size=7.4, color="white", weight="bold")
        text(x + 8.0, 76.2, title, size=7.7, weight="bold", ha="left")

    # Panel A: protocol identifiers disappear, repeated content markers remain.
    for y, color in ((62, COLORS["blue"]), (51, COLORS["teal"]), (40, COLORS["gold"])):
        node(8.0, y + 2.5, color=color, size=1.8)
        ax.add_patch(FancyBboxPatch((5.6, y - 2.2), 4.8, 3.0, boxstyle="round,pad=.1,rounding_size=.8", facecolor="white", edgecolor=color, linewidth=0.9))
        arrow((11.0, y), (16.0, y), color=color)
    text(8.0, 31.0, "Agent traffic", size=7.3, weight="bold")

    box(16.5, 42.0, 14.0, 21.0, fill=COLORS["light_blue"], edge=COLORS["blue"])
    text(23.5, 59.0, "Broker", size=8.0, weight="bold")
    for y, label in ((52.5, "user ID"), (47.2, "session")):
        box(19.1, y, 8.8, 3.7, fill="white", edge="#D6DCE2", radius=0.5)
        text(23.5, y + 1.85, label, size=6.2)
        ax.plot([20.0, 27.0], [y + 3.0, y + 0.7], color=COLORS["red"], linewidth=1.2)
    arrow((30.8, 52.5), (35.5, 52.5), color=COLORS["blue"], width=1.1)
    ax.add_patch(Ellipse((41.0, 58.2), 10.5, 7.2, facecolor=COLORS["light_teal"], edgecolor=COLORS["teal"], linewidth=1.0))
    text(41.0, 58.2, "Provider", size=7.0, weight="bold")
    for index in range(3):
        request_card(35.2 + index * 1.8, 39.2 - index * 1.4, color=COLORS["teal"])
    text(41.0, 33.5, "plaintext remains", size=7.0, color=COLORS["teal"], weight="bold")
    box(7.0, 8.0, 39.0, 15.0, fill=COLORS["light_gray"], edge="#D6DCE2")
    text(15.0, 19.0, "No caller IDs", size=6.4, color=COLORS["red"], weight="bold")
    box(11.8, 11.0, 8.5, 4.0, fill="white", edge="#D6DCE2", radius=0.5)
    ax.plot([12.7, 19.3], [14.2, 11.8], color=COLORS["red"], linewidth=1.1)
    text(36.5, 19.0, "Repeated handles", size=6.4, color=COLORS["gold"], weight="bold")
    for index in range(3):
        node(30.5 + index * 4.5, 12.8, color=COLORS["gold"], kind="diamond", size=1.35)

    # Panel B: visual evidence becomes clusters; a small inset carries the measurement contract.
    text(68.0, 69.5, "Visible evidence", size=7.2, color=COLORS["muted"], weight="bold")
    for index, color in enumerate((COLORS["blue"], COLORS["teal"], COLORS["gold"])):
        request_card(60.5 + index * 4.0, 49.0 - index * 3.5, color=color)
    arrow((80.2, 54.0), (84.2, 54.0), width=1.2)
    box(84.7, 57.0, 12.0, 6.0, fill=COLORS["light_blue"], edge=COLORS["blue"])
    text(90.7, 60.0, "CARP", size=7.3, weight="bold")
    box(84.7, 46.0, 12.0, 6.0, fill=COLORS["light_teal"], edge=COLORS["teal"])
    text(90.7, 49.0, "ASL", size=7.3, weight="bold")
    arrow((97.1, 60.0), (101.0, 57.0), color=COLORS["blue"])
    arrow((97.1, 49.0), (101.0, 52.0), color=COLORS["teal"])
    for cx, cy, color, kind in (
        (100.5, 39.5, COLORS["blue"], "circle"),
        (87.8, 37.5, COLORS["teal"], "diamond"),
    ):
        ax.add_patch(Ellipse((cx, cy), 13.0, 10.0, facecolor="white", edgecolor=color, linewidth=1.0))
        for dx, dy in ((-3.2, 1.3), (0.0, -1.0), (3.3, 1.4)):
            node(cx + dx, cy + dy, color=color, kind=kind, size=1.15)
    text(94.5, 29.8, "Pseudonymous clusters", size=7.3, weight="bold")

    box(61.5, 8.0, 41.5, 15.0, fill=COLORS["light_gray"], edge="#D6DCE2")
    text(70.0, 20.5, "Paired control", size=6.5, color=COLORS["gold"], weight="bold")
    request_card(63.5, 9.5, color=COLORS["gold"])
    text(78.0, 15.3, "↔", size=9.0, color=COLORS["gold"], weight="bold")
    request_card(80.5, 9.5, color=COLORS["muted"], marker=False)
    text(98.0, 20.5, "Δ linkage", size=6.5, color=COLORS["teal"], weight="bold")
    box(94.0, 11.0, 8.0, 4.2, fill="white", edge=COLORS["red"], dashed=True, radius=0.5)
    text(98.0, 13.1, "truth", size=6.3, color=COLORS["red"])

    # Panel C: workflow continuity grows into entity, profile, and later assignment.
    text(121.0, 69.5, "Workflows", size=7.2, color=COLORS["muted"], weight="bold")
    for y, color in ((62.0, COLORS["blue"]), (53.0, COLORS["teal"]), (44.0, COLORS["gold"])):
        workflow(114.5, y, color)
        arrow((125.5, y), (132.0, 53.0), color=color, width=0.8)
    hexagon = [(136, 58), (141, 55), (141, 49), (136, 46), (131, 49), (131, 55)]
    ax.add_patch(Polygon(hexagon, closed=True, facecolor=COLORS["light_gold"], edgecolor=COLORS["gold"], linewidth=1.1))
    node(136, 52.0, color=COLORS["gold"], kind="diamond", size=1.7)
    text(136.0, 42.0, "Persistent entity", size=7.0, color=COLORS["gold"], weight="bold")

    arrow((141.5, 54.0), (146.0, 62.0), color=COLORS["gold"])
    arrow((141.5, 50.0), (146.0, 34.0), color=COLORS["gold"])
    box(146.0, 56.0, 10.0, 14.0, fill=COLORS["light_teal"], edge=COLORS["teal"])
    for y, width in ((65.0, 6.2), (62.0, 4.5), (59.0, 7.0)):
        ax.add_patch(Rectangle((147.5, y), width, 0.7, facecolor=COLORS["teal"], edgecolor="none"))
    text(151.0, 52.5, "Profile", size=7.3, color=COLORS["teal"], weight="bold")

    box(145.5, 24.0, 11.0, 14.0, fill=COLORS["light_red"], edge=COLORS["red"])
    ax.plot([147.0, 154.8], [31.0, 31.0], color=COLORS["red"], linewidth=0.8)
    for x, color in ((148.0, COLORS["blue"]), (151.0, COLORS["teal"]), (154.0, COLORS["red"])):
        node(x, 31.0, color=color, size=1.05)
    text(151.0, 20.5, "Watchlist", size=7.3, color=COLORS["red"], weight="bold")

    arrow((115.0, 12.0), (153.5, 12.0), color=COLORS["gold"], width=1.2)
    text(115.0, 15.0, "continuity", size=6.6, color=COLORS["blue"], weight="bold", ha="left")
    text(153.5, 15.0, "later assignment", size=6.6, color=COLORS["red"], weight="bold", ha="right")

    arrow((51.5, 43.0), (55.0, 43.0), width=1.3)
    arrow((105.0, 43.0), (108.5, 43.0), width=1.3)
    fig.tight_layout(pad=0.2)
    return fig


def _visual_linkage_overview() -> plt.Figure:
    """Balanced main figure: visual narrative plus the paper's distinguishing mechanics."""
    fig, ax = plt.subplots(figsize=(7.0, 3.94))
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 90)
    ax.axis("off")

    def label(
        x: float,
        y: float,
        value: str,
        *,
        size: float = 6.8,
        color: str = COLORS["ink"],
        weight: str = "normal",
        ha: str = "center",
    ) -> None:
        ax.text(x, y, value, ha=ha, va="center", fontsize=size, color=color, weight=weight)

    def box(
        x: float,
        y: float,
        width: float,
        height: float,
        value: str = "",
        *,
        fill: str = "white",
        edge: str = COLORS["ink"],
        size: float = 6.5,
        dashed: bool = False,
        weight: str = "bold",
    ) -> None:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.15,rounding_size=0.8",
                facecolor=fill,
                edgecolor=edge,
                linewidth=1.0,
                linestyle="--" if dashed else "-",
            )
        )
        if value:
            label(x + width / 2, y + height / 2, value, size=size, weight=weight)

    def arrow(
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        color: str = COLORS["muted"],
        width: float = 0.9,
        dashed: bool = False,
    ) -> None:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=7,
                color=color,
                linewidth=width,
                linestyle="--" if dashed else "-",
            )
        )

    def node(x: float, y: float, color: str, *, diamond: bool = False, size: float = 1.2) -> None:
        if diamond:
            points = [(x, y + size), (x + size, y), (x, y - size), (x - size, y)]
            ax.add_patch(Polygon(points, closed=True, facecolor="white", edgecolor=color, linewidth=0.9))
        else:
            ax.add_patch(Circle((x, y), size, facecolor="white", edgecolor=color, linewidth=0.9))

    def request(x: float, y: float, *, edge: str, marker: bool = True, scale: float = 1.0) -> None:
        width, height = 10.5 * scale, 6.8 * scale
        box(x, y, width, height, fill="white", edge=edge)
        for offset, line_width in ((4.9, 5.5), (3.5, 7.3), (2.1, 4.3)):
            ax.add_patch(
                Rectangle(
                    (x + 1.1 * scale, y + offset * scale),
                    line_width * scale,
                    0.36 * scale,
                    facecolor="#D6DCE2",
                    edgecolor="none",
                )
            )
        if marker:
            node(x + 8.5 * scale, y + 5.0 * scale, COLORS["gold"], diamond=True, size=0.75 * scale)

    def section(y: float, title: str) -> None:
        label(2.0, y, title, size=7.2, color=COLORS["muted"], weight="bold", ha="left")

    label(80, 87.0, "From Unidentified Requests to Longitudinal Linkage", size=10.0, weight="bold")
    label(
        80,
        83.5,
        "Read left to right: observe what remains, reconstruct hidden groups, then follow them over time.",
        size=6.7,
        color=COLORS["muted"],
    )

    # Section 1: provider visibility and paired measurement.
    section(79.0, "1  PROVIDER VIEW + PAIRED MEASUREMENT")
    for y, color in ((71.5, COLORS["blue"]), (66.0, COLORS["teal"]), (60.5, COLORS["gold"])):
        node(5.0, y + 1.2, color, size=1.15)
        ax.add_patch(FancyBboxPatch((3.6, y - 1.8), 2.8, 1.9, boxstyle="round,pad=.1,rounding_size=.5", facecolor="white", edgecolor=color, linewidth=0.8))
        arrow((6.7, y), (9.0, y), color=color, width=0.7)
    box(9.3, 61.0, 12.0, 12.5, fill=COLORS["light_blue"], edge=COLORS["blue"])
    label(15.3, 70.2, "Broker", size=7.5, weight="bold")
    box(12.0, 63.0, 6.5, 3.0, "IDs", fill="white", edge="#D6DCE2", size=5.8)
    ax.plot([12.6, 18.0], [65.6, 63.4], color=COLORS["red"], linewidth=1.0)
    arrow((21.6, 67.2), (25.0, 67.2), color=COLORS["blue"], width=1.0)
    for index in range(3):
        request(25.2 + index * 1.7, 63.0 - index * 1.3, edge=COLORS["teal"], scale=0.85)
    label(30.5, 58.5, "IDs disappear; content repeats", size=6.1, color=COLORS["teal"], weight="bold")

    arrow((36.8, 67.0), (40.0, 67.0), width=1.0)
    box(40.3, 59.2, 40.0, 15.5, fill=COLORS["light_gray"], edge="#D6DCE2")
    label(49.0, 72.0, "Original", size=6.4, color=COLORS["gold"], weight="bold")
    request(43.0, 62.3, edge=COLORS["gold"], scale=0.8)
    label(56.0, 66.0, "↔", size=8.0, color=COLORS["gold"], weight="bold")
    request(59.0, 62.3, edge=COLORS["muted"], marker=False, scale=0.8)
    label(68.0, 72.0, "Paired intervention", size=6.4, color=COLORS["gold"], weight="bold")
    for x, value in ((43.0, "handles"), (54.0, "replay"), (64.0, "timing / collision")):
        box(x, 59.8, 9.2 if x < 64 else 13.2, 2.1, value, fill="white", edge=COLORS["gold"], size=4.9, weight="normal")

    arrow((80.8, 67.0), (84.0, 67.0), width=1.0)
    box(84.3, 61.5, 14.0, 11.0, "Run the same\nCARP / ASL", fill=COLORS["light_red"], edge=COLORS["red"], size=6.4)
    arrow((98.7, 67.0), (102.0, 67.0), width=1.0)
    box(102.3, 62.0, 28.0, 10.0, "Did linkage drop?\nIdentify the signal", fill=COLORS["light_gray"], edge=COLORS["ink"], size=6.8)
    box(106.0, 57.0, 18.0, 3.8, "sealed truth: scoring only", fill="white", edge=COLORS["red"], size=4.9, dashed=True, weight="normal")
    arrow((115.0, 60.9), (116.0, 61.8), color=COLORS["red"], dashed=True)

    ax.plot([2, 158], [55.0, 55.0], color="#D6DCE2", linewidth=0.8)

    # Section 2: enough method detail to show novelty without configuration-level clutter.
    section(52.5, "2  TWO WAYS TO RECONSTRUCT HIDDEN GROUPS")
    for index, color in enumerate((COLORS["blue"], COLORS["teal"], COLORS["gold"])):
        request(3.0 + index * 1.2, 38.8 + index * 1.0, edge=color, scale=0.72)
    label(9.0, 36.8, "visible evidence", size=6.0, color=COLORS["muted"], weight="bold")
    arrow((13.5, 43.0), (17.0, 43.0), width=1.0)

    box(17.3, 45.0, 11.0, 5.5, "CARP", fill=COLORS["light_blue"], edge=COLORS["blue"], size=7.4)
    carp = [
        (31.0, "Block & index", "find likely pairs"),
        (52.0, "Refine candidates", "verify continuity"),
        (73.0, "Propagate handles", "connect workflows"),
    ]
    for x, title, explanation in carp:
        box(x, 44.2, 17.0, 7.0, fill=COLORS["light_blue"], edge=COLORS["blue"])
        label(x + 8.5, 48.4, title, size=5.6, weight="bold")
        label(x + 8.5, 45.8, explanation, size=5.1, color=COLORS["muted"])
    for start, end in ((28.5, 30.7), (48.3, 51.7), (69.3, 72.7)):
        arrow((start, 47.7), (end, 47.7), color=COLORS["blue"])

    box(17.3, 34.0, 11.0, 5.5, "ASL", fill=COLORS["light_teal"], edge=COLORS["teal"], size=7.4)
    asl = [
        (31.0, "Agent state", "track bounded history"),
        (52.0, "Support vs conflict", "weigh evidence"),
        (73.0, "Selective hierarchy", "link or abstain"),
    ]
    for x, title, explanation in asl:
        box(x, 33.2, 17.0, 7.0, fill=COLORS["light_teal"], edge=COLORS["teal"])
        label(x + 8.5, 37.4, title, size=5.6, weight="bold")
        label(x + 8.5, 34.8, explanation, size=5.1, color=COLORS["muted"])
    for start, end in ((28.5, 30.7), (48.3, 51.7), (69.3, 72.7)):
        arrow((start, 36.7), (end, 36.7), color=COLORS["teal"])

    arrow((90.5, 47.7), (95.0, 44.5), color=COLORS["blue"])
    arrow((90.5, 36.7), (95.0, 40.0), color=COLORS["teal"])
    for cx, cy, color, diamond in ((102.0, 45.0, COLORS["blue"], False), (116.0, 39.0, COLORS["teal"], True)):
        ax.add_patch(Ellipse((cx, cy), 15.0, 10.5, facecolor="white", edgecolor=color, linewidth=1.0))
        for dx, dy in ((-3.5, 1.4), (0.0, -1.3), (3.5, 1.4)):
            node(cx + dx, cy + dy, color, diamond=diamond, size=1.1)
    label(109.0, 31.5, "Recovered workflows and entities", size=6.4, weight="bold")
    arrow((124.0, 42.0), (131.5, 42.0), width=0.9, dashed=True)
    box(132.0, 35.0, 24.0, 12.5, "Avoid all-pairs\nReject weak links", fill=COLORS["light_gray"], edge=COLORS["ink"], size=6.2)

    ax.plot([2, 158], [27.8, 27.8], color="#D6DCE2", linewidth=0.8)

    # Section 3: name the three channels, then visualize their hierarchy of consequences.
    section(25.2, "3  WHAT EACH SIGNAL REVEALS")
    chips = [
        (3.0, 17.0, "Direct exposure\nread fields", COLORS["light_red"], COLORS["red"]),
        (22.0, 21.0, "Continuity\ngroup one task", COLORS["light_blue"], COLORS["blue"]),
        (45.0, 25.0, "Propagation\nconnect later tasks", COLORS["light_gold"], COLORS["gold"]),
    ]
    for x, width, value, fill, edge in chips:
        box(x, 15.5, width, 6.5, value, fill=fill, edge=edge, size=5.8)

    arrow((70.5, 18.8), (74.0, 18.8), width=1.0)
    for index in range(3):
        node(75.5 + index * 5.0, 18.8, COLORS["blue"], size=1.0)
        if index < 2:
            arrow((76.7 + index * 5.0, 18.8), (79.3 + index * 5.0, 18.8), color=COLORS["blue"], width=0.7)
    label(80.5, 13.5, "workflow", size=5.8, color=COLORS["blue"], weight="bold")
    arrow((86.8, 18.8), (91.0, 18.8), color=COLORS["blue"])
    hexagon = [(95, 23), (100, 20), (100, 14), (95, 11), (90, 14), (90, 20)]
    ax.add_patch(Polygon(hexagon, closed=True, facecolor=COLORS["light_gold"], edgecolor=COLORS["gold"], linewidth=1.0))
    node(95, 17.0, COLORS["gold"], diamond=True, size=1.5)
    label(95, 8.5, "same project / customer", size=5.6, color=COLORS["gold"], weight="bold")
    arrow((100.5, 19.5), (105.0, 22.0), color=COLORS["gold"])
    arrow((100.5, 14.5), (105.0, 11.5), color=COLORS["gold"])
    box(105.3, 19.5, 18.0, 6.0, "Aggregate\nPartial profile", fill=COLORS["light_teal"], edge=COLORS["teal"], size=6.0)
    box(105.3, 8.0, 18.0, 6.0, "Recognize later\nWatchlist", fill=COLORS["light_red"], edge=COLORS["red"], size=6.0)
    arrow((123.7, 17.0), (129.0, 17.0), width=1.0)
    box(129.3, 11.0, 27.0, 12.0, "New requests join\nthe earlier component", fill=COLORS["light_gold"], edge=COLORS["gold"], size=6.6)

    fig.tight_layout(pad=0.2)
    return fig


def _evidence_layers() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    ax.axis("off")
    columns = ["Dataset", "Trace substrate", "Reliable truth", "Paper role"]
    rows = [
        (
            "Open-SWE",
            "Real software-agent traces",
            "workflow, repo, owner-like",
            "Main real-data evidence",
            COLORS["light_blue"],
        ),
        (
            "tau-bench historical",
            "Real tool-agent traces",
            "workflow/session",
            "Non-code external validity",
            COLORS["light_teal"],
        ),
        (
            "Hierarchy overlay",
            "Real traces + controlled overlay",
            "user / tenant / project",
            "Longitudinal mechanism",
            COLORS["light_gold"],
        ),
        (
            "Controlled replay",
            "Re-keyed public traces",
            "known workflow structure",
            "Computation scale",
            COLORS["light_red"],
        ),
    ]
    x_positions = [0.02, 0.24, 0.51, 0.74]
    widths = [0.20, 0.25, 0.21, 0.24]
    header_y = 0.86
    for x, width, label in zip(x_positions, widths, columns, strict=True):
        ax.add_patch(
            FancyBboxPatch(
                (x, header_y),
                width,
                0.10,
                boxstyle="round,pad=0.01,rounding_size=0.01",
                facecolor=COLORS["ink"],
                edgecolor=COLORS["ink"],
                transform=ax.transAxes,
            )
        )
        ax.text(
            x + width / 2,
            header_y + 0.05,
            label,
            color="white",
            ha="center",
            va="center",
            weight="bold",
            transform=ax.transAxes,
        )
    for row_index, row in enumerate(rows):
        y = 0.68 - row_index * 0.19
        values = row[:4]
        fill = row[4]
        for x, width, value in zip(x_positions, widths, values, strict=True):
            ax.add_patch(
                FancyBboxPatch(
                    (x, y),
                    width,
                    0.14,
                    boxstyle="round,pad=0.01,rounding_size=0.01",
                    facecolor=fill,
                    edgecolor="white",
                    linewidth=1.0,
                    transform=ax.transAxes,
                )
            )
            ax.text(
                x + width / 2,
                y + 0.07,
                value,
                ha="center",
                va="center",
                wrap=True,
                fontsize=7.2,
                color=COLORS["ink"],
                transform=ax.transAxes,
            )
    ax.text(
        0.5,
        0.02,
        "Each evidence layer supports a different question: exposure, continuity, hierarchy, or scale.",
        ha="center",
        color=COLORS["muted"],
        fontsize=7,
        transform=ax.transAxes,
    )
    fig.tight_layout(pad=0.25)
    return fig


def _t3_longitudinal() -> plt.Figure:
    levels = ["User", "Project", "Organization"]
    baseline = np.array([0.214, 0.159, 0.297])
    baseline_precision = np.array([0.954, 1.000, 1.000])
    baseline_recall = np.array([0.121, 0.087, 0.174])
    percolation = np.array([0.771, 0.686, 0.777])
    percolation_precision = np.array([0.952, 0.998, 1.000])
    percolation_recall = np.array([0.648, 0.522, 0.635])
    watchlist = np.array([0.702, 0.830, 0.876])
    watchlist_precision = np.array([0.950, 1.000, 1.000])
    watchlist_recall = np.array([0.557, 0.709, 0.779])
    percolation_low = np.array([0.733, 0.653, 0.756])
    percolation_high = np.array([0.805, 0.717, 0.796])
    watchlist_low = np.array([0.675, 0.816, 0.860])
    watchlist_high = np.array([0.725, 0.840, 0.891])
    x = np.arange(len(levels))
    width = 0.23
    fig, ax = plt.subplots(figsize=(5.0, 3.25))
    ax.bar(x - width, baseline, width, label="Bucket-local cold start", color=COLORS["muted"])
    ax.bar(
        x,
        percolation,
        width,
        label="Cross-cache stable-handle linkage",
        color=COLORS["teal"],
        yerr=np.vstack((percolation - percolation_low, percolation_high - percolation)),
        capsize=2.5,
        error_kw={"linewidth": 0.8},
    )
    ax.bar(
        x + width,
        watchlist,
        width,
        label="Later-traffic watchlist",
        color=COLORS["gold"],
        yerr=np.vstack((watchlist - watchlist_low, watchlist_high - watchlist)),
        capsize=2.5,
        error_kw={"linewidth": 0.8},
    )
    ax.set_ylabel("Score")
    ax.set_xlabel("Bars: F1;  △ precision;  ● recall", fontsize=7)
    ax.set_xticks(x, levels)
    ax.set_ylim(0, 1.06)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.grid(axis="y", color="#D9DEE3", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    for positions, precision, recall in (
        (x - width, baseline_precision, baseline_recall),
        (x, percolation_precision, percolation_recall),
        (x + width, watchlist_precision, watchlist_recall),
    ):
        ax.scatter(
            positions,
            precision,
            marker="^",
            s=18,
            facecolors="white",
            edgecolors=COLORS["ink"],
            linewidths=0.7,
            zorder=4,
        )
        ax.scatter(
            positions,
            recall,
            marker="o",
            s=13,
            color=COLORS["ink"],
            linewidths=0.5,
            zorder=4,
        )
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles,
        labels,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        fontsize=6.3,
        ncol=3,
        columnspacing=0.9,
        handletextpad=0.4,
    )
    ax.set_title("Persistent Handles Enable Longitudinal Linkage", weight="bold", pad=28)
    for positions, values in ((x - width, baseline), (x, percolation), (x + width, watchlist)):
        for position, value in zip(positions, values, strict=True):
            ax.text(position, value + 0.025, f"{value:.2f}", ha="center", va="bottom", fontsize=6.8)
    fig.tight_layout(pad=0.4)
    return fig


def _results_overview() -> plt.Figure:
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.25))
    ax_surface, ax_time, ax_scale, ax_bound = axes

    surface_labels = ["Raw", "$-$handles", "$-$replay", "$-$both"]
    surface_f1 = [0.967, 0.183, 0.117, 0.016]
    surface_colors = [COLORS["blue"], COLORS["gold"], COLORS["teal"], COLORS["red"]]
    bars = ax_surface.bar(surface_labels, surface_f1, color=surface_colors, width=0.68)
    ax_surface.set_ylim(0, 1.05)
    ax_surface.set_ylabel("F1")
    ax_surface.set_title("A  Distinct channels", loc="left", weight="bold", fontsize=8)
    for bar, value in zip(bars, surface_f1, strict=True):
        ax_surface.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.025,
            f"{value:.3f}",
            ha="center",
            fontsize=5.8,
        )

    concurrency = [2, 10, 41, 146]
    temporal = [0.736, 0.125, 0.035, 0.013]
    content = [0.960, 0.960, 0.960, 0.960]
    ax_time.plot(concurrency, temporal, marker="o", color=COLORS["red"], label="Time buckets")
    ax_time.plot(
        concurrency,
        content,
        marker="s",
        color=COLORS["teal"],
        label="Content stage",
    )
    ax_time.set_xscale("log")
    ax_time.set_xticks(concurrency, [str(value) for value in concurrency])
    ax_time.set_ylim(0, 1.05)
    ax_time.set_xlabel("Concurrent workflows")
    ax_time.set_title("B  Timing fails with overlap", loc="left", weight="bold", fontsize=8)
    ax_time.legend(frameon=False, fontsize=5.8, loc="center right", handlelength=1.2)

    domains = ["Open-SWE\nincremental", "tau-bench\nhistorical"]
    generic_text = np.array([0.204, 0.019])
    carp = np.array([0.107, 0.104])
    asl = np.array([0.394, 0.164])
    x = np.arange(len(domains))
    width = 0.23
    ax_scale.bar(
        x - width,
        generic_text,
        width,
        label="Generic text",
        color=COLORS["muted"],
        edgecolor=COLORS["ink"],
        linewidth=0.35,
        hatch="//",
    )
    ax_scale.bar(
        x,
        carp,
        width,
        label="CARP",
        color=COLORS["blue"],
        edgecolor=COLORS["ink"],
        linewidth=0.35,
        hatch="\\\\",
    )
    ax_scale.bar(
        x + width,
        asl,
        width,
        label="ASL",
        color=COLORS["teal"],
        edgecolor=COLORS["ink"],
        linewidth=0.35,
        hatch="..",
    )
    ax_scale.set_xticks(x, domains)
    ax_scale.set_ylim(0, 0.45)
    ax_scale.set_title("C  Agent state raises F1", loc="left", weight="bold", fontsize=8)
    ax_scale.legend(
        frameon=False,
        fontsize=5.5,
        ncol=1,
        loc="upper right",
        borderaxespad=0.2,
        labelspacing=0.25,
    )
    for positions, values in (
        (x - width, generic_text),
        (x, carp),
        (x + width, asl),
    ):
        for position, value in zip(positions, values, strict=True):
            ax_scale.text(position, value + 0.012, f"{value:.2f}", ha="center", fontsize=5.5)

    multiplicity = np.array([1, 2, 4, 8, 16])
    f1_bound = np.array([1.000, 0.600, 0.333, 0.176, 0.091])
    carp_f1 = np.array([1.000, 0.600, 0.333, 0.000, 0.000])
    ax_bound.plot(
        multiplicity,
        f1_bound,
        marker="o",
        color=COLORS["ink"],
        label="Expected F1 bound",
    )
    ax_bound.plot(
        multiplicity,
        carp_f1,
        marker="s",
        color=COLORS["teal"],
        label="CARP",
    )
    ax_bound.set_xscale("log", base=2)
    ax_bound.set_xticks(multiplicity, [str(value) for value in multiplicity])
    ax_bound.set_ylim(0, 1.05)
    ax_bound.set_xlabel("Entities / equiv. class")
    ax_bound.set_title("D  Ambiguity bounds F1", loc="left", weight="bold", fontsize=8)
    ax_bound.legend(frameon=False, fontsize=5.8, handlelength=1.2)

    for ax in (ax_surface, ax_time, ax_scale, ax_bound):
        ax.grid(axis="y", color="#D9DEE3", linewidth=0.55)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="both", labelsize=6)
    fig.subplots_adjust(left=0.065, right=0.995, bottom=0.22, top=0.88, wspace=0.38)
    return fig


def _save(
    fig: plt.Figure,
    base: Path,
    *,
    formats: tuple[str, ...] = ("pdf", "png"),
) -> list[Path]:
    outputs: list[Path] = []
    for extension in formats:
        path = base.with_suffix(f".{extension}")
        options = {"dpi": 240} if extension == "png" else {}
        fig.savefig(path, bbox_inches="tight", **options)
        outputs.append(path)
    plt.close(fig)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper figures.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/paper/figures"))
    parser.add_argument(
        "--figures",
        nargs="+",
        choices=("all", "carp_pipeline", "evidence_layers", "t3_longitudinal", "results_overview"),
        default=["all"],
    )
    parser.add_argument("--formats", nargs="+", choices=("pdf", "png"), default=["pdf", "png"])
    args = parser.parse_args()
    print(
        [
            str(path)
            for path in generate_figures(
                args.output_dir,
                selected=tuple(args.figures),
                formats=tuple(args.formats),
            )
        ]
    )


if __name__ == "__main__":
    main()
