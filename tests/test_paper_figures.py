from __future__ import annotations

from pathlib import Path

from agent_privacy.experiments.generate_paper_figures import generate_figures


def test_results_overview_figure_can_be_generated(tmp_path: Path) -> None:
    outputs = generate_figures(
        tmp_path,
        selected=("results_overview",),
        formats=("pdf",),
    )

    assert outputs == [tmp_path / "results_overview.pdf"]
    assert outputs[0].stat().st_size > 10_000


def test_all_paper_figures_can_be_generated(tmp_path: Path) -> None:
    outputs = generate_figures(tmp_path, selected=("all",), formats=("pdf",))

    assert {path.name for path in outputs} == {
        "carp_pipeline.pdf",
        "evidence_layers.pdf",
        "results_overview.pdf",
        "t3_longitudinal.pdf",
    }
    assert all(path.stat().st_size > 8_000 for path in outputs)
