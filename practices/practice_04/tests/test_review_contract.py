import pytest

from mcp.server.fastmcp.exceptions import ToolError

from mcp_server import check_review_payload
from review_contract import MAX_DIFF_BYTES, ContractError, check_payload


def test_accepts_small_diff():
    assert check_payload({"diff": "+line\n"}) == {
        "valid": True,
        "diff_utf8_bytes": 6,
        "limit_utf8_bytes": 16384,
    }


def test_requires_diff():
    with pytest.raises(ContractError) as error:
        check_payload({})

    assert error.value.code == "diff_required"


@pytest.mark.parametrize("diff", [None, 12, False, "", " \t\n"])
def test_rejects_missing_or_non_text_diff(diff):
    with pytest.raises(ContractError, match="Field diff is required"):
        check_payload({"diff": diff})


def test_accepts_exact_byte_limit():
    assert check_payload({"diff": "ё" * (MAX_DIFF_BYTES // 2)})["diff_utf8_bytes"] == MAX_DIFF_BYTES


def test_rejects_unicode_over_byte_limit():
    with pytest.raises(ContractError) as error:
        check_payload({"diff": "ё" * (MAX_DIFF_BYTES // 2 + 1)})
    assert error.value.code == "diff_too_large"


def test_rejects_non_object_payload_with_controlled_error():
    with pytest.raises(ContractError) as error:
        check_payload(None)

    assert error.value.code == "payload_object_required"


def test_counts_utf8_bytes_not_characters():
    assert check_payload({"diff": "+ёж\n"})["diff_utf8_bytes"] == 6


def test_rejects_oversized_diff():
    with pytest.raises(ContractError) as error:
        check_payload({"diff": "x" * (MAX_DIFF_BYTES + 1)})

    assert error.value.code == "diff_too_large"


def test_mcp_wrapper_returns_success():
    assert check_review_payload({"diff": "+line\n"})["valid"] is True


def test_mcp_wrapper_exposes_controlled_error():
    with pytest.raises(ToolError, match="diff_required"):
        check_review_payload({})
