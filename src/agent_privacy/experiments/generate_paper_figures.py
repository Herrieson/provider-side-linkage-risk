from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


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


def generate_figures(output_dir: Path) -> list[Path]:
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
    outputs = []
    outputs.extend(_save(_carp_pipeline(), output_dir / "carp_pipeline"))
    outputs.extend(_save(_evidence_layers(), output_dir / "evidence_layers"))
    outputs.extend(_save(_t3_longitudinal(), output_dir / "t3_longitudinal"))
    return outputs


def _carp_pipeline() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.0, 2.65))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
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
        fontsize: float = 7.2,
        linestyle: str = "-",
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
                mutation_scale=8,
                linewidth=1.0,
                color=color,
                connectionstyle=connectionstyle,
            )
        )

    ax.text(
        50,
        48.2,
        "Controlled measurement: provider-visible evidence remains separate from linkage truth",
        ha="center",
        va="center",
        weight="bold",
        fontsize=8.3,
    )
    add_box(1.0, 34.0, 13.0, 9.0, "Agent\ntraces", COLORS["light_gray"], COLORS["ink"])
    add_box(
        18.0,
        34.0,
        15.0,
        9.0,
        "Broker transform\nstrips caller IDs",
        COLORS["light_blue"],
        COLORS["blue"],
    )
    add_box(
        37.0,
        36.0,
        16.0,
        9.0,
        "Attack view\ncontent + allowed\ntelemetry",
        COLORS["light_teal"],
        COLORS["teal"],
        fontsize=6.5,
    )
    add_box(
        37.0,
        23.5,
        16.0,
        7.0,
        "Hidden truth\nlabels only",
        "white",
        COLORS["red"],
        fontsize=6.9,
        linestyle="--",
    )
    add_box(
        57.0,
        36.0,
        14.0,
        9.0,
        "Paired controls\nremove / perturb",
        COLORS["light_gold"],
        COLORS["gold"],
        fontsize=6.9,
    )
    add_box(
        75.0,
        36.0,
        11.0,
        9.0,
        "Reference\nattacks +\ndiagnostics",
        COLORS["light_red"],
        COLORS["red"],
        fontsize=6.4,
    )
    add_box(
        90.0,
        32.0,
        9.0,
        13.0,
        "Score +\nattribute\nrisk",
        COLORS["light_gray"],
        COLORS["ink"],
        fontsize=6.8,
    )
    add_arrow((14.4, 38.5), (17.6, 38.5))
    add_arrow((33.4, 39.2), (36.6, 40.1))
    add_arrow((33.4, 37.6), (36.6, 27.7), connectionstyle="arc3,rad=0.16")
    add_arrow((53.4, 40.5), (56.6, 40.5))
    add_arrow((71.4, 40.5), (74.6, 40.5))
    add_arrow((86.4, 40.5), (89.6, 39.5))
    add_arrow((53.4, 27.0), (94.0, 31.6), color=COLORS["red"], connectionstyle="arc3,rad=-0.10")
    ax.text(70.5, 26.1, "unsealed only for scoring", ha="center", color=COLORS["red"], fontsize=6.3)
    ax.text(45.0, 32.0, "attack cannot read", ha="center", color=COLORS["red"], fontsize=6.2)

    ax.plot([1.5, 98.5], [19.2, 19.2], color="#C8CFD6", linewidth=0.8)
    ax.text(
        50,
        17.1,
        "CARP reference attack: bounded sparse linkage before higher-cost reconstruction",
        ha="center",
        va="center",
        weight="bold",
        fontsize=7.7,
    )
    stages = [
        (1, 5, 17, 8, "1  Cache-local\nblocking", COLORS["light_gray"], COLORS["ink"]),
        (21, 5, 17, 8, "2  Typed-anchor\nindexes", COLORS["light_blue"], COLORS["blue"]),
        (41, 5, 17, 8, "3  Context\ncandidates", COLORS["light_gold"], COLORS["gold"]),
        (61, 5, 17, 8, "4  Budgeted\nrefinement", COLORS["light_teal"], COLORS["teal"]),
        (
            81,
            5,
            18,
            8,
            "5  Cross-cache\npropagation",
            COLORS["light_red"],
            COLORS["red"],
        ),
    ]
    for x, y, w, h, label, fill, edge in stages:
        add_box(x, y, w, h, label, fill, edge, fontsize=6.9)
    for start, end in ((18, 21), (38, 41), (58, 61), (78, 81)):
        add_arrow((start + 0.3, 9), (end - 0.3, 9))
    ax.text(
        50,
        1.7,
        "Outputs: workflow partitions  |  task-entity components  |  profiles  |  later-traffic watchlists",
        ha="center",
        va="center",
        fontsize=6.7,
        color=COLORS["ink"],
    )
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
            "Dataset B / T3",
            "Real traces + controlled overlay",
            "user / tenant / project",
            "Trace-grounded mechanism",
            COLORS["light_gold"],
        ),
        (
            "Synthetic A",
            "Controlled generated traffic",
            "full hierarchy + profile",
            "Scale and difficulty controls",
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
        "Claim strength follows the available truth: overlays and synthetic data are mechanism evidence, not real identity recovery.",
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
    fig, ax = plt.subplots(figsize=(5.0, 3.05))
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
    ax.set_ylim(0, 1.02)
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
    handles.extend(
        [
            Line2D(
                [0],
                [0],
                marker="^",
                linestyle="none",
                markerfacecolor="white",
                markeredgecolor=COLORS["ink"],
                markersize=4,
                label="Precision",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                color=COLORS["ink"],
                markersize=3.5,
                label="Recall",
            ),
        ]
    )
    labels.extend(["Precision", "Recall"])
    ax.legend(handles, labels, frameon=False, loc="upper left", fontsize=6.5, ncol=2)
    ax.set_title("T3: Persistent Handles Enable Later Tracking", weight="bold")
    for positions, values in ((x - width, baseline), (x, percolation), (x + width, watchlist)):
        for position, value in zip(positions, values, strict=True):
            ax.text(position, value + 0.025, f"{value:.2f}", ha="center", va="bottom", fontsize=6.8)
    fig.tight_layout(pad=0.4)
    return fig


def _save(fig: plt.Figure, base: Path) -> list[Path]:
    pdf = base.with_suffix(".pdf")
    png = base.with_suffix(".png")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return [pdf, png]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper figures.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/paper/figures"))
    args = parser.parse_args()
    print([str(path) for path in generate_figures(args.output_dir)])


if __name__ == "__main__":
    main()
