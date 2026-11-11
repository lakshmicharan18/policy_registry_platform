import pytest

from app.api.routers.onboarding import parse_csv


def test_parse_csv_preserves_headers_and_values() -> None:
    headers, sample_rows, row_count = parse_csv(b"col1,col2\nWH001, 24 \nWH002,8\n")

    assert headers == ["col1", "col2"]
    assert sample_rows[0] == {"col1": "WH001", "col2": " 24 "}
    assert row_count == 2


@pytest.mark.parametrize("content", [b"", b"col1,col1\na,b\n", b"col1,\na,b\n"])
def test_parse_csv_rejects_empty_or_invalid_headers(content: bytes) -> None:
    with pytest.raises(ValueError):
        parse_csv(content)
