"""Groq API integration — chat and tool-using assistant."""

import json
import os

from groq import Groq

from docs_tool import append_to_doc
from gmail_tool import create_email_draft

DEFAULT_MODEL = "llama-3.3-70b-versatile"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "append_to_doc",
            "description": "Append text to the end of a Google Doc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Google Doc ID from the document URL.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text to append to the document.",
                    },
                },
                "required": ["doc_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_email_draft",
            "description": "Create a Gmail draft email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address."},
                    "subject": {"type": "string", "description": "Email subject."},
                    "body": {"type": "string", "description": "Email body text."},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to Google Docs and Gmail tools. "
    "Use append_to_doc to edit documents and create_email_draft to compose emails. "
    "Ask for missing details before calling a tool."
)


def _get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to .env or Railway variables."
        )
    return Groq(api_key=api_key)


def _run_tool(name: str, arguments: dict) -> dict:
    if name == "append_to_doc":
        return append_to_doc(arguments["doc_id"], arguments["content"])
    if name == "create_email_draft":
        return create_email_draft(
            arguments["to"], arguments["subject"], arguments["body"]
        )
    raise ValueError(f"Unknown tool: {name}")


def chat(message: str, model: str = DEFAULT_MODEL) -> str:
    """Send a message to Groq and return the reply."""
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content or ""


def run_assistant(message: str, model: str = DEFAULT_MODEL) -> dict:
    """Use Groq with Google tool calling to handle a user request."""
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    tool_results = []

    for _ in range(5):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in (assistant_message.tool_calls or [])
                ]
                or None,
            }
        )

        if not assistant_message.tool_calls:
            return {
                "reply": assistant_message.content or "",
                "tool_results": tool_results,
            }

        for call in assistant_message.tool_calls:
            args = json.loads(call.function.arguments)
            result = _run_tool(call.function.name, args)
            tool_results.append({"tool": call.function.name, "args": args, "result": result})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str),
                }
            )

    return {
        "reply": "I could not finish the request within the tool call limit.",
        "tool_results": tool_results,
    }
