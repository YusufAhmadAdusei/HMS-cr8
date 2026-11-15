from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from .prompts import AGENT_SYSTEM_PROMPT
from .tools import build_health_tools

load_dotenv()


class Agent:
    """Tool-using agent for evidence-grounded health explanations."""

    def __init__(self, summary: dict[str, Any]) -> None:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            api_key=api_key,
        )
        self.tools = build_health_tools(summary)
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=AGENT_SYSTEM_PROMPT,
        )

    def chat(self, message: str) -> str:
        if not message.strip():
            raise ValueError("Message cannot be empty")
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]}
        )
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("Agent returned no messages")
        content: Any = messages[-1].content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            content = "\n".join(part for part in text_parts if part)
        if not str(content).strip():
            raise RuntimeError("Agent returned an empty response")
        return str(content)

def answer_question(question: str, summary: dict[str, Any]) -> str:
    return Agent(summary).chat(question)


def display_tool_info(summary: dict[str, Any]) -> None:
    for registered_tool in build_health_tools(summary):
        print(f"\nName: {registered_tool.name}")
        print(f"Description: {registered_tool.description}")
        print(f"Arguments: {registered_tool.args}")
