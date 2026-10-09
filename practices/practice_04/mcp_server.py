import json

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from review_contract import ContractError, check_payload

mcp = FastMCP("review-contract")


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def check_review_payload(payload: dict) -> dict:
    """Проверить payload перед отправкой на code review."""
    try:
        return check_payload(payload)
    except ContractError as error:
        raise ToolError(json.dumps({"code": error.code, "message": error.message})) from None


if __name__ == "__main__":
    mcp.run(transport="stdio")
