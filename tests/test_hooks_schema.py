#!/usr/bin/env python3
"""test_hooks_schema.py — hermetic schema tests for the plugin hook configs.

Guards hooks/hooks.json and hooks/cursor-hooks.json against the class of bug
found in v2.4.1: a `"type": "prompt"` entry on `SessionStart`. SessionStart
fires before any conversation exists, so a prompt hook has no injection target.
It did nothing and raised a hook error on every session open.

Checks:
  1. Both files are valid JSON with the expected top-level shape.
  2. Event names are known.
  3. Each hook declares a valid `type` and the payload key that type needs.
  4. SessionStart accepts `command` hooks only.
  5. SessionStart matcher tokens are valid.
  6. Every command hook is syntactically valid shell (`bash -n`).
  7. Cursor hooks carry commands only (Cursor cannot inject prompts).
  8. The hot-cache restore command hook still exists.

No network, no LLM. Pure stdlib plus bash.

Usage:
  python3 tests/test_hooks_schema.py
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_HOOKS = ROOT / "hooks" / "hooks.json"
CURSOR_HOOKS = ROOT / "hooks" / "cursor-hooks.json"

# Claude Code lifecycle events this plugin is allowed to register.
KNOWN_EVENTS = {
    "SessionStart",
    "Stop",
    "PreToolUse",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
}

# Hook types and the payload key each one requires.
TYPE_PAYLOAD = {
    "command": "command",
    "prompt": "prompt",
    "http": "url",
    "agent": "agent",
}

# Events that fire with no conversation in place. A prompt hook has nowhere to
# inject on these, so only command hooks are legal. Inject startup context by
# writing to STDOUT from a command hook instead.
COMMAND_ONLY_EVENTS = {"SessionStart"}

# Valid SessionStart matcher tokens (the matcher is a `|` alternation).
SESSION_START_MATCHERS = {"startup", "resume", "clear", "compact"}


class Fail(SystemExit):
    pass


def assert_eq(label, expected, actual):
    if expected != actual:
        raise Fail(f"FAIL {label}: expected {expected!r}, got {actual!r}")
    print(f"OK   {label}")


def assert_true(label, cond, detail=""):
    if not cond:
        raise Fail(f"FAIL {label}{': ' + detail if detail else ''}")
    print(f"OK   {label}")


def load(path):
    if not path.is_file():
        raise Fail(f"FAIL missing hook config: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise Fail(f"FAIL invalid JSON in {path.name}: {exc}")


def iter_claude_hooks(cfg):
    """Yield (event, matcher, index, hook) for every Claude hook entry."""
    for event, entries in cfg["hooks"].items():
        for entry in entries:
            for i, hook in enumerate(entry.get("hooks", [])):
                yield event, entry.get("matcher", ""), i, hook


# ─── Shape ───────────────────────────────────────────────────────────────────
def test_claude_shape():
    cfg = load(CLAUDE_HOOKS)
    assert_true("hooks.json has top-level hooks object",
                isinstance(cfg.get("hooks"), dict))
    for event, entries in cfg["hooks"].items():
        assert_true(f"{event} value is a list", isinstance(entries, list))
        assert_true(f"{event} has at least one entry", len(entries) > 0)
        for entry in entries:
            assert_true(f"{event} entry has string matcher",
                        isinstance(entry.get("matcher", ""), str))
            assert_true(f"{event} entry has non-empty hooks list",
                        isinstance(entry.get("hooks"), list) and entry["hooks"])
    return cfg


def test_event_names_known(cfg):
    unknown = sorted(set(cfg["hooks"]) - KNOWN_EVENTS)
    assert_eq("all event names known", [], unknown)


# ─── Hook types and payloads ─────────────────────────────────────────────────
def test_hook_types_valid(cfg):
    for event, _, i, hook in iter_claude_hooks(cfg):
        t = hook.get("type")
        assert_true(f"{event}[{i}] type is known",
                    t in TYPE_PAYLOAD, f"got {t!r}")
        key = TYPE_PAYLOAD[t]
        val = hook.get(key)
        assert_true(f"{event}[{i}] type={t} carries non-empty {key}",
                    isinstance(val, str) and val.strip() != "")


def test_no_prompt_hook_on_command_only_events(cfg):
    """The v2.4.1 regression gate."""
    offenders = [
        f"{event}[{i}]"
        for event, _, i, hook in iter_claude_hooks(cfg)
        if event in COMMAND_ONLY_EVENTS and hook.get("type") != "command"
    ]
    assert_eq(f"{'/'.join(sorted(COMMAND_ONLY_EVENTS))} carries command hooks only",
              [], offenders)


def test_session_start_matchers(cfg):
    for entry in cfg["hooks"].get("SessionStart", []):
        tokens = [t for t in entry.get("matcher", "").split("|") if t]
        assert_true("SessionStart matcher is non-empty", bool(tokens))
        bad = sorted(set(tokens) - SESSION_START_MATCHERS)
        assert_eq("SessionStart matcher tokens valid", [], bad)


# ─── Command hooks are runnable shell ────────────────────────────────────────
def test_command_hooks_parse_as_shell(cfg):
    for event, _, i, hook in iter_claude_hooks(cfg):
        if hook.get("type") != "command":
            continue
        proc = subprocess.run(
            ["bash", "-n"], input=hook["command"],
            text=True, capture_output=True,
        )
        assert_eq(f"{event}[{i}] command parses as shell", 0, proc.returncode)


# ─── Hot-cache restore path must survive ─────────────────────────────────────
def test_hot_cache_restore_present(cfg):
    """SessionStart STDOUT is the only working hot-cache restore path.

    Removing this hook kills the feature silently, so pin it.
    """
    found = any(
        hook.get("type") == "command" and "wiki/hot.md" in hook.get("command", "")
        for event, _, _, hook in iter_claude_hooks(cfg)
        if event == "SessionStart"
    )
    assert_true("SessionStart still cats wiki/hot.md", found)


# ─── Cursor config ───────────────────────────────────────────────────────────
def test_cursor_hooks_are_commands_only():
    cfg = load(CURSOR_HOOKS)
    assert_true("cursor-hooks.json declares a version", "version" in cfg)
    assert_true("cursor-hooks.json has top-level hooks object",
                isinstance(cfg.get("hooks"), dict))
    for event, entries in cfg["hooks"].items():
        assert_true(f"cursor {event} value is a list", isinstance(entries, list))
        for i, hook in enumerate(entries):
            cmd = hook.get("command")
            assert_true(f"cursor {event}[{i}] has non-empty command",
                        isinstance(cmd, str) and cmd.strip() != "")
            assert_true(f"cursor {event}[{i}] declares no prompt",
                        "prompt" not in hook,
                        "Cursor cannot inject prompts; use rules/vault-os.mdc")
            proc = subprocess.run(
                ["bash", "-n"], input=cmd, text=True, capture_output=True,
            )
            assert_eq(f"cursor {event}[{i}] command parses as shell",
                      0, proc.returncode)


def main():
    print("=== test_hooks_schema.py ===")
    cfg = test_claude_shape()
    test_event_names_known(cfg)
    test_hook_types_valid(cfg)
    test_no_prompt_hook_on_command_only_events(cfg)
    test_session_start_matchers(cfg)
    test_command_hooks_parse_as_shell(cfg)
    test_hot_cache_restore_present(cfg)
    test_cursor_hooks_are_commands_only()
    print("\nAll hook schema tests passed.")


if __name__ == "__main__":
    main()
