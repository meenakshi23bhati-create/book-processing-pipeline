"""
🤖 RAG Agent — ReAct-style Multi-Step Reasoning
=================================================
Agent decides WHICH tools to call, in WHAT order, and HOW MANY times
before producing a final answer. Tools available:
  1. search_chunks      — vector + keyword search over book content
  2. get_chat_history   — retrieve similar past Q&A pairs
  3. get_book_memory    — fetch start / middle / end context
  4. generate_answer    — call Groq LLaMA3 with assembled context
"""

import time
import json
import requests
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.service.chat_service import (
    search_similar_chunks,
    get_similar_past_questions,
    get_book_memory,
    save_chat_history,
    simple_extractive_answer,
)

# ─── Tool Registry ────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_chunks",
        "description": (
            "Search the book for chunks relevant to the query using "
            "vector similarity + keyword hybrid search. "
            "Call this when you need factual content from the book."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":  {"type": "string", "description": "Search query"},
                "top_k":  {"type": "integer", "description": "Number of chunks to retrieve (default 6)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_chat_history",
        "description": (
            "Retrieve semantically similar questions that were asked before. "
            "Call this to avoid repeating work and to surface cached answers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Current user query"},
                "top_k": {"type": "integer", "description": "Max past Q&A pairs to return (default 3)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_book_memory",
        "description": (
            "Fetch the beginning, middle, and end excerpts of the book "
            "to provide structural context. Useful for broad questions about "
            "the overall book content or narrative arc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class AgentStep:
    step_number: int
    thought: str
    tool_called: str | None = None
    tool_input: dict = field(default_factory=dict)
    tool_result: Any = None
    elapsed: float = 0.0


@dataclass
class AgentResult:
    answer: str
    sources: list
    steps: list
    similar_questions: list
    total_time: float
    query: str
    book_id: int


# ─── Tool Executor ────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict, book_id: int) -> Any:
    """Run a tool and return its raw result."""
    if tool_name == "search_chunks":
        query = tool_input.get("query", "")
        top_k = int(tool_input.get("top_k", 6))
        return search_similar_chunks(query, book_id, top_k=top_k)

    elif tool_name == "get_chat_history":
        query = tool_input.get("query", "")
        top_k = int(tool_input.get("top_k", 3))
        return get_similar_past_questions(query, book_id, top_k=top_k)

    elif tool_name == "get_book_memory":
        return get_book_memory(book_id)

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ─── Groq LLM caller ─────────────────────────────────────────────────────────

def _call_groq(messages: list, system_prompt: str, max_tokens: int = 2048) -> str:
    """Call Groq LLaMA3 and return the text response."""
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        print(f"⚠️ Groq status {resp.status_code}: {resp.text[:200]}")
        return ""
    except Exception as e:
        print(f"❌ Groq error: {e}")
        return ""


# ─── ReAct Agent Loop ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a book-reading assistant that answers questions using a RAG pipeline.

You have access to these tools:
{tools_json}

Respond ONLY with valid JSON in one of these two formats:

FORMAT A — Use a tool:
{{
  "thought": "<your reasoning>",
  "action": "<tool_name>",
  "action_input": {{ ... }}
}}

FORMAT B — Final answer (when you have enough context):
{{
  "thought": "<your reasoning>",
  "final_answer": "<complete answer to the user's question>"
}}

Rules:
- Always start by checking chat history to avoid duplicate work.
- Use search_chunks for specific factual questions.
- Use get_book_memory for broad/summary questions.
- After collecting context, produce a final_answer.
- Maximum 5 reasoning steps — then produce final_answer.
- Do NOT wrap JSON in markdown code fences.
"""


def run_agent(book_id: int, query: str, max_steps: int = 5) -> AgentResult:
    """
    Execute the ReAct agent loop.

    1. Agent decides which tool to call (Thought → Action → Observation).
    2. Loops until it emits a `final_answer` or hits max_steps.
    3. Falls back to extractive answer if LLM fails.
    """
    start_time = time.time()
    steps: list[AgentStep] = []
    context_chunks: list = []
    similar_questions: list = []

    tools_json = json.dumps(TOOLS, indent=2)
    system_prompt = _SYSTEM_PROMPT.format(tools_json=tools_json)

    # Conversation history for the agent
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Book ID: {book_id}\n"
                f"User Question: {query}\n\n"
                "Decide which tools to call and then produce your final answer."
            ),
        }
    ]

    print(f"\n{'='*60}")
    print(f"🤖 AGENT START  | Book {book_id} | Query: {query}")
    print(f"{'='*60}")

    final_answer = ""

    for step_num in range(1, max_steps + 1):
        step_start = time.time()
        print(f"\n--- Step {step_num}/{max_steps} ---")

        # Ask the LLM for next action
        raw = _call_groq(messages, system_prompt, max_tokens=512)

        if not raw:
            print("⚠️ Empty LLM response — stopping agent loop.")
            break

        # Parse the JSON response
        try:
            # Strip accidental markdown fences
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            decision = json.loads(clean)
        except json.JSONDecodeError:
            print(f"⚠️ JSON parse error:\n{raw[:300]}")
            break

        thought = decision.get("thought", "")
        print(f"💭 Thought: {thought}")

        # ── Final answer ───────────────────────────────────────────────────
        if "final_answer" in decision:
            final_answer = decision["final_answer"]
            step = AgentStep(
                step_number=step_num,
                thought=thought,
                tool_called=None,
                elapsed=round(time.time() - step_start, 2),
            )
            steps.append(step)
            print(f"✅ Agent produced final_answer at step {step_num}")
            break

        # ── Tool call ──────────────────────────────────────────────────────
        tool_name = decision.get("action", "")
        tool_input = decision.get("action_input", {})

        if not tool_name:
            print("⚠️ No action or final_answer in response — stopping.")
            break

        print(f"🔧 Tool: {tool_name} | Input: {tool_input}")

        tool_result = execute_tool(tool_name, tool_input, book_id)
        elapsed = round(time.time() - step_start, 2)

        # Accumulate context
        if tool_name == "search_chunks" and isinstance(tool_result, list):
            context_chunks.extend(tool_result)
            # Deduplicate by chunk id
            seen = set()
            context_chunks = [
                c for c in context_chunks
                if c["id"] not in seen and not seen.add(c["id"])  # type: ignore[func-returns-value]
            ]

        elif tool_name == "get_chat_history" and isinstance(tool_result, list):
            similar_questions = [
                {
                    "question": q["question"],
                    "answer": q["answer"],
                    "similarity": round(float(q["similarity"]), 3),
                }
                for q in tool_result
                if float(q["similarity"]) > 0.75
            ]

        # Summarise the tool result for the LLM (keep it short)
        if tool_name == "search_chunks" and isinstance(tool_result, list):
            obs_text = "\n".join(
                f"[Chunk {c['chunk_index']} | Pages {c['start_page']}-{c['end_page']}]\n{c['row_text'][:400]}"
                for c in tool_result[:4]
            )
        elif tool_name == "get_chat_history" and isinstance(tool_result, list):
            obs_text = "\n".join(
                f"Q: {q['question']}\nA: {q['answer'][:200]}"
                for q in tool_result[:3]
            ) or "No past questions found."
        elif tool_name == "get_book_memory":
            mem: dict = tool_result if isinstance(tool_result, dict) else {}
            obs_text = (
                f"Total chunks: {mem.get('total_chunks', 0)}\n"
                f"Start: {mem.get('start', [])}\n"
                f"Middle: {mem.get('middle', [])}\n"
                f"End: {mem.get('end', [])}"
            )[:800]
        else:
            obs_text = str(tool_result)[:600]

        step = AgentStep(
            step_number=step_num,
            thought=thought,
            tool_called=tool_name,
            tool_input=tool_input,
            tool_result=obs_text[:300],
            elapsed=elapsed,
        )
        steps.append(step)

        # Feed observation back into conversation
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": f"Observation from {tool_name}:\n{obs_text}\n\nContinue — call another tool or produce final_answer.",
        })

        print(f"   ✅ Tool done ({elapsed}s) | Observation: {obs_text[:120]}...")

    # ─── Fallback: extractive answer if agent didn't produce one ─────────────
    if not final_answer:
        print("⚠️ Agent loop ended without final_answer — using extractive fallback.")
        if context_chunks:
            final_answer = simple_extractive_answer(query, context_chunks)
        else:
            # Last resort: do a direct chunk search
            context_chunks = search_similar_chunks(query, book_id, top_k=5)
            final_answer = simple_extractive_answer(query, context_chunks)

    # ─── Build sources list ───────────────────────────────────────────────────
    sources = [
        {
            "pages": f"Pages {c['start_page']}-{c['end_page']}",
            "similarity": round(float(c["similarity"]), 3),
            "summary": (c.get("summary") or "")[:200],
        }
        for c in context_chunks[:6]
    ]

    total_time = round(time.time() - start_time, 2)

    # ─── Persist to chat history ──────────────────────────────────────────────
    save_chat_history(book_id, query, final_answer)

    print(f"\n{'='*60}")
    print(f"🎯 FINAL ANSWER : {final_answer[:300]}")
    print(f"⏱️  TOTAL TIME   : {total_time}s | Steps: {len(steps)}")
    print(f"{'='*60}\n")

    return AgentResult(
        answer=final_answer,
        sources=sources,
        steps=[
            {
                "step": s.step_number,
                "thought": s.thought,
                "tool": s.tool_called,
                "tool_input": s.tool_input,
                "observation": s.tool_result,
                "elapsed_seconds": s.elapsed,
            }
            for s in steps
        ],
        similar_questions=similar_questions,
        total_time=total_time,
        query=query,
        book_id=book_id,
    )