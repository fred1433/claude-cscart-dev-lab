#!/usr/bin/env python3
"""Turn each evidence/sessions/<id>/stream*.jsonl into a readable transcript.md.

Keeps every tool call (exact input), every tool result (truncated to 1500
characters, flagged when it is an error), hook decisions, the final answer and
the init inventory (model, version, mode, tools, MCP servers, plugins).

    python3 tools/summarize_sessions.py [evidence/sessions]
"""
import glob
import json
import os
import sys

LAB = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for item in content or []:
        if isinstance(item, dict):
            parts.append(item.get("text") or json.dumps(item)[:300])
    return "\n".join(parts)


def summarize(stream_path):
    lines = ["## %s" % os.path.basename(stream_path), ""]
    for raw in open(stream_path):
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        kind, sub = event.get("type"), event.get("subtype")
        if kind == "system" and sub == "init":
            lines.append("- init: model `%s`, Claude Code `%s`, permissionMode `%s`, MCP servers %s, plugins %s" % (
                event.get("model"), event.get("claude_code_version"), event.get("permissionMode"),
                event.get("mcp_servers"), [p.get("name") for p in event.get("plugins") or []]))
            lines.append("- tools: %s" % ", ".join(event.get("tools") or []))
        elif kind == "system" and sub == "hook_response":
            lines.append("- hook `%s` exit %s: %s" % (event.get("hook_name"), event.get("exit_code"),
                                                  (event.get("stderr") or event.get("output") or "").strip()[:400]))
        elif kind == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    lines.append("- **tool call** `%s` %s" % (block["name"], json.dumps(block["input"])[:1200]))
                elif block.get("type") == "text" and block.get("text", "").strip():
                    lines.append("- assistant: %s" % block["text"].strip().replace("\n", "\n  ")[:3000])
        elif kind == "user":
            for block in event.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    flag = "ERROR " if block.get("is_error") else ""
                    body = text_of(block.get("content")).strip().replace("\n", "\n    ")
                    lines.append("- **tool result** %s%s" % (flag, body[:1500]))
        elif kind == "result":
            lines.append("- result: %s, %s turns, %s ms, permission_denials: %s" % (
                sub, event.get("num_turns"), event.get("duration_ms"),
                json.dumps(event.get("permission_denials"))[:1500]))
    return "\n".join(lines) + "\n"


def main(root):
    for folder in sorted(glob.glob(os.path.join(root, "s*"))):
        parts = ["# Transcript %s\n" % os.path.basename(folder),
                 "Generated from the raw stream*.jsonl files in this folder by tools/summarize_sessions.py "
                 "(long results truncated; the long dash character is rendered as --).\n"]
        for stream in sorted(glob.glob(os.path.join(folder, "stream*.jsonl"))):
            parts.append(summarize(stream))
        text = "\n".join(parts).replace("\u2014", "--")
        with open(os.path.join(folder, "transcript.md"), "w") as handle:
            handle.write(text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(LAB, "evidence", "sessions"))
