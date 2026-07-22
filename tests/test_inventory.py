from pathlib import Path

from agri_cv_novelty.inventory import summarize_csv


def test_summarize_csv_handles_utf8_sig(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("\ufeffname,year\nMuST-C,2025\nTomatoMAP,2026\n", encoding="utf-8")

    summary = summarize_csv(csv_path)

    assert summary.rows == 2
    assert summary.columns == ("name", "year")

