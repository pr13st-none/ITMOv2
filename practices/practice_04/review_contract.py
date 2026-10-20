MAX_DIFF_BYTES = 16 * 1024


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def check_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ContractError("payload_object_required", "Payload must be a JSON object")

    diff = payload.get("diff")
    if not isinstance(diff, str) or not diff.strip():
        raise ContractError("diff_required", "Field diff is required")

    if "\x00" in diff:
        raise ContractError("diff_binary", "diff must be text without NUL bytes")

    size = len(diff.encode("utf-8"))
    if size > MAX_DIFF_BYTES:
        raise ContractError("diff_too_large", f"diff exceeds {MAX_DIFF_BYTES} UTF-8 bytes")

    return {
        "valid": True,
        "diff_utf8_bytes": size,
        "limit_utf8_bytes": MAX_DIFF_BYTES,
    }
