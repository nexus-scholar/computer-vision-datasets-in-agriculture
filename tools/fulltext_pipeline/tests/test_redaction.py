from agri_fulltext.io_utils import redact_secrets
from agri_fulltext.acquisition import _redact_url


def test_redact_secrets_handles_api_and_signed_url_parameters():
    value = (
        "https://example.org/paper.pdf?api_key=abc&email=x@y.test&token=t123"
        "&X-Amz-Signature=deadbeef&safe=1"
    )
    redacted = redact_secrets(value)
    assert "abc" not in redacted
    assert "x@y.test" not in redacted
    assert "t123" not in redacted
    assert "deadbeef" not in redacted
    assert "safe=1" in redacted


def test_acquisition_audit_url_redaction_preserves_nonsecret_query_values():
    value = "https://example.org/paper.pdf?signature=secret&download=1"
    redacted = _redact_url(value)
    assert "secret" not in redacted
    assert "signature=REDACTED" in redacted
    assert "download=1" in redacted
