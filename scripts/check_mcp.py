"""Verify tool discovery and a harmless API call through the real stdio transport."""
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT/'plugin'/'cortes-ia'/'server.py')])
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.list_tools()
            names = [tool.name for tool in result.tools]
            assert set(names) == {'list_projects', 'get_project', 'analyze_project', 'transcribe_project', 'render_clip'}
            response = await session.call_tool('list_projects', {})
            assert not response.is_error
            print('MCP: 5 ferramentas descobertas e list_projects executado com sucesso.')


if __name__ == '__main__':
    asyncio.run(main())
