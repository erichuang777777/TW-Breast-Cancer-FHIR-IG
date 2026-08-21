import zipfile
from types import SimpleNamespace

from scripts import check_no_phi
from scripts.check_no_phi import scan


def test_git_nul_paths_preserve_unicode_and_spaces(monkeypatch):
    monkeypatch.setattr(
        check_no_phi.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="交接說明.md\0folder/a b.xlsx\0"),
    )
    assert check_no_phi._git("ls-files", "-z", nul_delimited=True) == [
        "交接說明.md", "folder/a b.xlsx"
    ]


def test_plain_text_identifier_is_detected(tmp_path):
    candidate = tmp_path / "notes.txt"
    candidate.write_text("patient " + "C1" + "23456789", encoding="utf-8")
    findings = scan(candidate, tmp_path)
    assert len(findings) == 1
    assert "疑似身分證／居留證號" in findings[0]


def test_office_open_xml_payload_is_scanned(tmp_path):
    candidate = tmp_path / "report.xlsx"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<si><t>patient " + "C1" + "23456789</t></si></sst>",
        )
    findings = scan(candidate, tmp_path)
    assert len(findings) == 1
    assert "report.xlsx!xl/sharedStrings.xml" in findings[0]


def test_declared_synthetic_identifier_is_allowed_in_office_file(tmp_path):
    candidate = tmp_path / "synthetic.docx"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr("word/document.xml", "<w:t>Z000000000</w:t>")
    assert scan(candidate, tmp_path) == []


def test_opaque_sensitive_binary_is_never_silently_skipped(tmp_path):
    candidate = tmp_path / "report.pdf"
    candidate.write_bytes(b"%PDF-1.7")
    findings = scan(candidate, tmp_path)
    assert len(findings) == 1
    assert "無法自動檢查的敏感二進位格式 .pdf" in findings[0]


def test_unknown_binary_is_never_silently_skipped(tmp_path):
    candidate = tmp_path / "unknown.bin"
    candidate.write_bytes(b"\xff\xff\x00\x01")
    findings = scan(candidate, tmp_path)
    assert len(findings) == 1
    assert "無法解碼檢查的二進位內容" in findings[0]


def test_declared_big5_xml_is_decoded_and_scanned(tmp_path):
    candidate = tmp_path / "legacy.xml"
    payload = '<?xml version="1.0" encoding="Big5"?><name>病人</name>'
    candidate.write_bytes(payload.encode("big5"))
    assert scan(candidate, tmp_path) == []
