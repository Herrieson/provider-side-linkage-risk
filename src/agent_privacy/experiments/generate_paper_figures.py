from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
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
        "carp_pipeline": _carp_pipeline,
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
    fig, ax = plt.subplots(figsize=(7.0, 3.15))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
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
        58.0,
        "Controlled measurement: provider-visible evidence remains separate from linkage truth",
        ha="center",
        va="center",
        weight="bold",
        fontsize=8.3,
    )
    add_box(1.0, 43.0, 13.0, 9.0, "Agent\ntraces", COLORS["light_gray"], COLORS["ink"])
    add_box(
        18.0,
        43.0,
        15.0,
        9.0,
        "Broker transform\nstrips caller IDs",
        COLORS["light_blue"],
        COLORS["blue"],
    )
    add_box(
        37.0,
        45.0,
        16.0,
        9.0,
        "Provider view\ncontent + allowed\ntelemetry",
        COLORS["light_teal"],
        COLORS["teal"],
        fontsize=6.5,
    )
    add_box(
        37.0,
        32.5,
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
        45.0,
        14.0,
        9.0,
        "Paired controls\nremove / perturb",
        COLORS["light_gold"],
        COLORS["gold"],
        fontsize=6.9,
    )
    add_box(
        75.0,
        45.0,
        11.0,
        9.0,
        "Linkage\nmethods",
        COLORS["light_red"],
        COLORS["red"],
        fontsize=6.4,
    )
    add_box(
        90.0,
        41.0,
        9.0,
        13.0,
        "Score +\nattribute\nrisk",
        COLORS["light_gray"],
        COLORS["ink"],
        fontsize=6.8,
    )
    add_arrow((14.4, 47.5), (17.6, 47.5))
    add_arrow((33.4, 48.2), (36.6, 49.1))
    add_arrow((33.4, 46.6), (36.6, 36.7), connectionstyle="arc3,rad=0.16")
    add_arrow((53.4, 49.5), (56.6, 49.5))
    add_arrow((71.4, 49.5), (74.6, 49.5))
    add_arrow((86.4, 49.5), (89.6, 48.5))
    add_arrow((53.4, 36.0), (94.0, 40.6), color=COLORS["red"], connectionstyle="arc3,rad=-0.10")
    ax.text(70.5, 35.1, "unsealed only for scoring", ha="center", color=COLORS["red"], fontsize=6.3)
    ax.text(45.0, 41.0, "attack cannot read", ha="center", color=COLORS["red"], fontsize=6.2)

    ax.plot([1.5, 98.5], [28.0, 28.0], color="#C8CFD6", linewidth=0.8)
    ax.text(
        50,
        26.0,
        "Two complementary bounded linkage paths",
        ha="center",
        va="center",
        weight="bold",
        fontsize=7.7,
    )
    add_box(1.0, 16.0, 9.0, 7.0, "CARP", COLORS["light_blue"], COLORS["blue"], fontsize=7.5)
    carp_stages = [
        (12.0, "Block +\nindex"),
        (33.5, "Context\ncandidates"),
        (55.0, "Budgeted\nrefinement"),
        (76.5, "Typed-handle\npropagation"),
    ]
    for x, label in carp_stages:
        add_box(x, 16.0, 19.0, 7.0, label, COLORS["light_blue"], COLORS["blue"], fontsize=6.8)
    for start, end in ((10.0, 12.0), (31.0, 33.5), (52.5, 55.0), (74.0, 76.5)):
        add_arrow((start + 0.2, 19.5), (end - 0.2, 19.5))

    add_box(1.0, 6.0, 9.0, 7.0, "ASL", COLORS["light_teal"], COLORS["teal"], fontsize=7.5)
    asl_stages = [
        (12.0, "Bounded\nAgent state"),
        (33.5, "Multi-view\ncandidates"),
        (55.0, "Support--conflict\ngate"),
        (76.5, "Selective\nhierarchy"),
    ]
    for x, label in asl_stages:
        add_box(x, 6.0, 19.0, 7.0, label, COLORS["light_teal"], COLORS["teal"], fontsize=6.8)
    for start, end in ((10.0, 12.0), (31.0, 33.5), (52.5, 55.0), (74.0, 76.5)):
        add_arrow((start + 0.2, 9.5), (end - 0.2, 9.5))
    ax.text(
        50,
        1.8,
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
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8))
    ax_surface, ax_time, ax_scale, ax_bound = axes.flat

    surface_labels = ["Raw\ncumulative", "No direct\nhandles", "No replay", "Neither"]
    surface_f1 = [0.967, 0.183, 0.117, 0.016]
    surface_colors = [COLORS["blue"], COLORS["gold"], COLORS["teal"], COLORS["red"]]
    bars = ax_surface.bar(surface_labels, surface_f1, color=surface_colors, width=0.68)
    ax_surface.set_ylim(0, 1.05)
    ax_surface.set_ylabel("Session F1")
    ax_surface.set_title("A  Paired removal isolates two channels", loc="left", weight="bold")
    for bar, value in zip(bars, surface_f1, strict=True):
        ax_surface.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.025,
            f"{value:.3f}",
            ha="center",
            fontsize=7,
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
    ax_time.set_xlabel("Peak concurrent workflows")
    ax_time.set_ylabel("Session F1")
    ax_time.set_title("B  Timing fails under concurrency", loc="left", weight="bold")
    ax_time.legend(frameon=False, fontsize=7, loc="center right")

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
    )
    ax_scale.bar(x, carp, width, label="CARP", color=COLORS["blue"])
    ax_scale.bar(x + width, asl, width, label="ASL", color=COLORS["teal"])
    ax_scale.set_xticks(x, domains)
    ax_scale.set_ylim(0, 0.45)
    ax_scale.set_ylabel("Session F1")
    ax_scale.set_title("C  Agent state improves linkage", loc="left", weight="bold")
    ax_scale.legend(
        frameon=False,
        fontsize=6.5,
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
            ax_scale.text(position, value + 0.012, f"{value:.2f}", ha="center", fontsize=6.5)

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
    ax_bound.set_xlabel("Exchangeable entities/class")
    ax_bound.set_ylabel("Pairwise F1")
    ax_bound.set_title("D  Indistinguishability bounds linkage", loc="left", weight="bold")
    ax_bound.legend(frameon=False, fontsize=7)

    for ax in (ax_surface, ax_time, ax_scale, ax_bound):
        ax.grid(axis="y", color="#D9DEE3", linewidth=0.55)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Key Findings Across Channels, Agent State, and Limits", weight="bold", y=1.01)
    fig.subplots_adjust(left=0.09, right=0.91, bottom=0.10, top=0.91, wspace=0.48, hspace=0.48)
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
