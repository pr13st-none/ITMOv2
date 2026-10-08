import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_mcp_stdio_success_and_invalid_inputs():
    async def exercise():
        root = Path(__file__).resolve().parents[1]
        server = StdioServerParameters(
            command=sys.executable, args=[str(root / "mcp_server.py")], cwd=root
        )
        async with stdio_client(server) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                tools = await client.list_tools()
                assert [tool.name for tool in tools.tools] == ["check_review_payload"]
                assert tools.tools[0].annotations.readOnlyHint is True

                good = await client.call_tool("check_review_payload", {"payload": {"diff": "+ёж\n"}})
                assert not good.isError
                assert json.loads(good.content[0].text)["diff_utf8_bytes"] == 6

                for payload, code in [({}, "diff_required"),
                                      ({"diff": "x" * 16385}, "diff_too_large"),
                                      ({"diff": "+" + chr(0)}, "diff_binary")]:
                    bad = await client.call_tool("check_review_payload", {"payload": payload})
                    assert bad.isError
                    assert code in bad.content[0].text

                wrong_type = await client.call_tool("check_review_payload", {"payload": []})
                assert wrong_type.isError

    asyncio.run(asyncio.wait_for(exercise(), timeout=30))
