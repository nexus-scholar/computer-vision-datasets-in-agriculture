from agri_fulltext.processing import _append_docling_ocr_flags


def test_docling_ocr_policy_for_born_digital_pdf():
    command = ["docling", "convert"]
    _append_docling_ocr_flags(command, {"recommended_ocr": False})
    assert command[-1] == "--no-ocr"
    assert "--force-ocr" not in command


def test_docling_ocr_policy_for_scanned_pdf():
    command = ["docling", "convert-remote"]
    _append_docling_ocr_flags(
        command,
        {"recommended_ocr": True, "force_ocr_recommended": True},
    )
    assert command[-2:] == ["--ocr", "--force-ocr"]
