import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI


APFEL_BASE_URL = os.getenv("APFEL_BASE_URL", "http://localhost:11434/v1")
APFEL_API_KEY = os.getenv("APFEL_API_KEY", "unused")
MODEL = os.getenv("APFEL_MODEL", "apple-foundationmodel")
SYSTEM_PROMPT = os.getenv(
    "CHATBOT_SYSTEM_PROMPT",
    "You are a helpful, concise assistant. Use available tools when appropriate.",
)
MAX_TOOL_ROUNDS = 8


def openai_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    definitions = []
    for tool in mcp_tools:
        schema = tool.input_schema if hasattr(tool, "input_schema") else tool.inputSchema
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": schema,
                },
            }
        )
    return definitions


def mcp_result_text(result: Any) -> str:
    parts = []
    for item in result.content:
        if hasattr(item, "text"):
            parts.append(item.text)
        elif hasattr(item, "model_dump"):
            parts.append(json.dumps(item.model_dump()))
        else:
            parts.append(str(item))
    is_error = result.is_error if hasattr(result, "is_error") else result.isError
    if is_error:
        return f"MCP tool error: {' '.join(parts)}"
    return "\n".join(parts)


async def answer_with_tools(
    client: OpenAI,
    session: ClientSession,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> str:
    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools or None,
        )
        #Inspect the response to see if it contains tool calls
        if not response.choices:
            raise RuntimeError("No response from the model.")
        else:
            print(f"Model response: {response.choices[0].message.content}")
        
        assistant = response.choices[0].message
        tool_calls = assistant.tool_calls or []

        if not tool_calls:
            answer = assistant.content or ""
            messages.append({"role": "assistant", "content": answer})
            return answer

        messages.append(
            {
                "role": "assistant",
                "content": assistant.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
                result = await session.call_tool(call.function.name, arguments=arguments)
                content = mcp_result_text(result)
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                content = f"Could not execute tool arguments: {error}"
            except Exception as error:
                content = f"Could not execute MCP tool: {error}"

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": content,
                }
            )

    raise RuntimeError("Apfel requested too many consecutive tool calls.")


async def chat() -> None:
    server_path = Path(__file__).with_name("server.js")
    server_parameters = StdioServerParameters(
        command="node",
        args=[str(server_path)],
        env=os.environ.copy(),
    )
    client = OpenAI(base_url=APFEL_BASE_URL, api_key=APFEL_API_KEY)

    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_result = await session.list_tools()
            tools = openai_tools(tool_result.tools)
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]

            print(
                f"Chatbot ready ({MODEL}); discovered {len(tools)} MCP tool(s). "
                "Type /reset to clear history or /quit to exit."
            )
            while True:
                try:
                    prompt = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break

                if not prompt:
                    continue
                if prompt.lower() in {"/quit", "/exit"}:
                    break
                if prompt.lower() == "/reset":
                    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                    print("Conversation reset.")
                    continue

                messages.append({"role": "user", "content": prompt})
                try:
                    answer = await answer_with_tools(client, session, messages, tools)
                except Exception as error:
                    messages.pop()
                    print(f"Error: {error}")
                    continue
                print(f"Assistant: {answer}\n")


if __name__ == "__main__":
    asyncio.run(chat())
