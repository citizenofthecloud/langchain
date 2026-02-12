"""
Example: LangChain agent that verifies other agents before interacting.

This agent has access to the Citizen of the Cloud identity tools.
It can look up agents, verify their cryptographic identity, and
check trust scores as part of its reasoning chain.

Requirements:
    pip install citizenofthecloud citizenofthecloud-langchain langchain-openai

Environment:
    OPENAI_API_KEY=sk-...
    CLOUD_ID=cc-...
    CLOUD_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
"""

import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from citizenofthecloud_langchain import (
    VerifyAgentTool,
    LookupAgentTool,
    CheckTrustTool,
    CloudIdentityHTTPClient,
)


def main():
    # ── Identity tools for the agent ──
    tools = [
        VerifyAgentTool(),
        LookupAgentTool(),
        CheckTrustTool(),
    ]

    # ── LLM and prompt ──
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are ResearchBot, an autonomous research agent registered "
         "with Citizen of the Cloud. You have access to identity "
         "verification tools.\n\n"
         "RULES:\n"
         "- Before delegating work to another agent, always check their "
         "trust score using the check_agent_trust tool.\n"
         "- Before processing data from another agent, verify their "
         "identity using the verify_cloud_agent tool.\n"
         "- Do not interact with agents that have a trust score below 0.5.\n"
         "- Do not interact with agents that have not signed the covenant.\n"
         "- If verification fails, explain why and refuse to proceed."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # ── Build and run ──
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Example 1: Check an agent before interacting
    print("\n" + "=" * 60)
    print("Example 1: Pre-interaction trust check")
    print("=" * 60)

    result = executor.invoke({
        "input": (
            "I need to send sensitive research data to agent "
            "cc-7f3a9b2e-4d1c-8e7f-a3b2-9c1d5e8f4a6b. "
            "Check if they're trustworthy enough. "
            "I require a minimum trust score of 0.7."
        )
    })
    print(f"\nResult: {result['output']}")

    # Example 2: Look up an agent's profile
    print("\n" + "=" * 60)
    print("Example 2: Agent profile lookup")
    print("=" * 60)

    result = executor.invoke({
        "input": (
            "Tell me everything about agent "
            "cc-82d8afc8-d1ef-4ec7-b3d0-6e613ea683ab. "
            "What do they do? Are they trustworthy?"
        )
    })
    print(f"\nResult: {result['output']}")


if __name__ == "__main__":
    main()
