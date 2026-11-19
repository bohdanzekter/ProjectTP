"""Command-line interface for SIPL Language Toolkit."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sipl import __version__
from sipl.errors import SiplRuntimeError, SiplSyntaxError
from sipl.interpreter import Interpreter, TraceEvent
from sipl.parser import parse, parse_to_concrete_tree
from sipl.visualization import (
    VisNode,
    ast_to_vis,
    parse_tree_to_vis,
    render_comparison_html,
    render_dot,
    render_json,
    render_svg,
    render_text,
)

EXIT_OK = 0
EXIT_SYNTAX_ERROR = 1
EXIT_RUNTIME_ERROR = 2
EXIT_INPUT_ERROR = 3


class CliInputError(Exception):
    """Raised when CLI input files or state arguments are invalid."""


def _parse_set_items(items: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        if "=" not in item:
            raise CliInputError(f"Invalid --set argument {item!r}; expected NAME=INT")
        name, raw_val = item.split("=", 1)
        name = name.strip()
        if not name:
            raise CliInputError(f"Empty variable name in --set argument {item!r}")
        try:
            value = int(raw_val.strip())
        except ValueError as exc:
            raise CliInputError(
                f"Invalid integer value in --set {item!r}: {raw_val!r}"
            ) from exc
        result[name] = value
    return result


def _validate_state_dict(data: object, source_label: str) -> dict[str, int]:
    if not isinstance(data, dict):
        raise CliInputError(f"State in {source_label} must be a JSON object")
    validated: dict[str, int] = {}
    for key, val in data.items():
        if not isinstance(key, str) or not key:
            raise CliInputError(f"Variable name in {source_label} must be a non-empty string")
        if not isinstance(val, int) or isinstance(val, bool):
            raise CliInputError(
                f"Value for variable {key!r} in {source_label} must be an integer"
            )
        validated[key] = val
    return validated


def _load_initial_state(args: argparse.Namespace) -> dict[str, int]:
    state: dict[str, int] = {}

    state_file: str | None = getattr(args, "state_file", None)
    if state_file is not None:
        path = Path(state_file)
        if not path.is_file():
            raise CliInputError(f"State file not found: {state_file}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CliInputError(f"Invalid JSON in state file {state_file}: {exc}") from exc
        state.update(_validate_state_dict(raw, state_file))

    state_json: str | None = getattr(args, "state", None)
    if state_json is not None:
        try:
            raw = json.loads(state_json)
        except json.JSONDecodeError as exc:
            raise CliInputError(f"Invalid JSON in --state: {exc}") from exc
        state.update(_validate_state_dict(raw, "--state"))

    set_items: list[str] = getattr(args, "set_vars", []) or []
    if set_items:
        state.update(_parse_set_items(set_items))

    return state


def _read_source(file_path: str) -> str:
    path = Path(file_path)
    if not path.is_file():
        raise CliInputError(f"Source file not found: {file_path}")
    return path.read_text(encoding="utf-8")


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _emit_error(
    command: str,
    file_path: str,
    as_json: bool,
    err_type: str,
    message: str,
    exit_code: int,
    extra_error: dict[str, Any] | None = None,
    partial_trace: list[TraceEvent] | None = None,
) -> int:
    if as_json:
        err_obj: dict[str, Any] = extra_error if extra_error is not None else {
            "type": err_type,
            "message": message,
            "span": None,
        }
        payload: dict[str, Any] = {
            "ok": False,
            "command": command,
            "file": file_path,
            "error": err_obj,
        }
        if partial_trace is not None:
            payload["trace"] = [e.to_dict() for e in partial_trace]
        _print_json(payload)
    else:
        print(f"Error [{err_type}]: {message}", file=sys.stderr)
    return exit_code


def _cmd_parse(args: argparse.Namespace) -> int:
    source = _read_source(args.file)
    program = parse(source, filename=args.file)
    if args.json:
        _print_json(
            {
                "ok": True,
                "command": "parse",
                "file": args.file,
                "ast": program.to_dict(),
            }
        )
    else:
        print(json.dumps(program.to_dict(), ensure_ascii=False, indent=2))
    return EXIT_OK


def _cmd_check(args: argparse.Namespace) -> int:
    source = _read_source(args.file)
    parse(source, filename=args.file)
    if args.json:
        _print_json(
            {
                "ok": True,
                "command": "check",
                "file": args.file,
                "valid": True,
            }
        )
    else:
        print(f"OK: {args.file} is syntactically valid.")
    return EXIT_OK


def _cmd_run(args: argparse.Namespace) -> int:
    source = _read_source(args.file)
    initial_state = _load_initial_state(args)
    if args.max_steps <= 0:
        raise CliInputError("--max-steps must be a positive integer")
    program = parse(source, filename=args.file)
    result = Interpreter(max_steps=args.max_steps, collect_trace=False).run(
        program,
        initial_state=initial_state,
    )
    if args.json:
        _print_json(
            {
                "ok": True,
                "command": "run",
                "file": args.file,
                "steps": result.steps,
                "final_state": result.final_state.as_dict(),
            }
        )
    else:
        print(f"Finished in {result.steps} step(s).")
        print(f"Final state: {result.final_state.as_dict()}")
    return EXIT_OK


def _cmd_trace(args: argparse.Namespace) -> int:
    source = _read_source(args.file)
    initial_state = _load_initial_state(args)
    if args.max_steps <= 0:
        raise CliInputError("--max-steps must be a positive integer")
    program = parse(source, filename=args.file)

    collected: list[TraceEvent] = []
    interp = Interpreter(
        max_steps=args.max_steps,
        collect_trace=True,
        on_event=collected.append,
    )
    try:
        result = interp.run(program, initial_state=initial_state)
    except SiplRuntimeError as exc:
        return _emit_error(
            command="trace",
            file_path=args.file,
            as_json=args.json,
            err_type=type(exc).__name__,
            message=str(exc),
            exit_code=EXIT_RUNTIME_ERROR,
            extra_error=exc.to_dict(),
            partial_trace=collected,
        )

    if args.json:
        _print_json(
            {
                "ok": True,
                "command": "trace",
                "file": args.file,
                "steps": result.steps,
                "final_state": result.final_state.as_dict(),
                "trace": [e.to_dict() for e in result.trace],
            }
        )
    else:
        for ev in result.trace:
            print(ev.to_dict())
    return EXIT_OK

def _render_vis(root: VisNode, fmt: str, title: str) -> str:
    if fmt == "text":
        return render_text(root)
    if fmt == "json":
        return render_json(root)
    if fmt == "dot":
        return render_dot(root, title=title)
    if fmt == "svg":
        return render_svg(root, title=title)
    raise CliInputError(f"Unsupported visualization format: {fmt}")


def _write_or_print(content: str, out_path: str | None) -> None:
    if out_path is not None:
        Path(out_path).write_text(content, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        print(content)


def _cmd_vis_tree(args: argparse.Namespace) -> int:
    source = _read_source(args.file)
    tree = parse_to_concrete_tree(source, filename=args.file)
    vis = parse_tree_to_vis(tree, source, filename=args.file)
    rendered = _render_vis(vis, args.format, title=f"Parse Tree: {args.file}")
    _write_or_print(rendered, args.output)
    return EXIT_OK


def _cmd_vis_ast(args: argparse.Namespace) -> int:
    source = _read_source(args.file)
    program = parse(source, filename=args.file)
    vis = ast_to_vis(program, source)
    rendered = _render_vis(vis, args.format, title=f"AST: {args.file}")
    _write_or_print(rendered, args.output)
    return EXIT_OK


def _cmd_vis_compare(args: argparse.Namespace) -> int:
    source = _read_source(args.file)
    tree = parse_to_concrete_tree(source, filename=args.file)
    program = parse(source, filename=args.file)
    pt_vis = parse_tree_to_vis(tree, source, filename=args.file)
    ast_vis = ast_to_vis(program, source)
    html_out = render_comparison_html(source, pt_vis, ast_vis, filename=args.file)
    _write_or_print(html_out, args.output)
    return EXIT_OK

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sipl",
        description="SIPL Language Toolkit CLI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_parse = subparsers.add_parser("parse", help="Parse a SIPL file and output its AST")
    p_parse.add_argument("file", help="Path to .sipl file")
    p_parse.add_argument("--json", action="store_true", help="Output structured JSON")

    p_check = subparsers.add_parser("check", help="Check syntax of a SIPL file")
    p_check.add_argument("file", help="Path to .sipl file")
    p_check.add_argument("--json", action="store_true", help="Output structured JSON")

    for cmd_name, help_text in (
        ("run", "Run a SIPL program"),
        ("trace", "Run a SIPL program and output execution trace"),
    ):
        sub = subparsers.add_parser(cmd_name, help=help_text)
        sub.add_argument("file", help="Path to .sipl file")
        sub.add_argument("--state", help="Initial state as JSON object, e.g. '{\"M\": 8}'")
        sub.add_argument("--state-file", help="Path to JSON file with initial state")
        sub.add_argument(
            "--set",
            dest="set_vars",
            action="append",
            default=[],
            metavar="NAME=INT",
            help="Set variable value (can be repeated, e.g. --set M=8 --set N=16)",
        )
        sub.add_argument(
            "--max-steps",
            type=int,
            default=10_000,
            help="Maximum execution steps before aborting (default: 10000)",
        )
        sub.add_argument("--json", action="store_true", help="Output structured JSON")

    for cmd_name, help_text in (
            ("vis-tree", "Visualize concrete Parse Tree (text/json/dot/svg)"),
            ("vis-ast", "Visualize abstract syntax tree (text/json/dot/svg)"),
    ):
        sub_v = subparsers.add_parser(cmd_name, help=help_text)
        sub_v.add_argument("file", help="Path to .sipl file")
        sub_v.add_argument(
            "--format",
            choices=["text", "json", "dot", "svg"],
            default="text",
            help="Output format (default: text)",
        )
        sub_v.add_argument("-o", "--output", help="Optional output file path")

    p_cmp = subparsers.add_parser(
        "vis-compare",
        help="Generate interactive HTML comparing Parse Tree and AST",
    )
    p_cmp.add_argument("file", help="Path to .sipl file")
    p_cmp.add_argument("-o", "--output", help="Optional output HTML file path")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point returning a process exit code."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    command: str = args.command
    file_path: str = getattr(args, "file", "")
    as_json: bool = bool(getattr(args, "json", False))

    try:
        if command == "parse":
            return _cmd_parse(args)
        if command == "check":
            return _cmd_check(args)
        if command == "run":
            return _cmd_run(args)
        if command == "trace":
            return _cmd_trace(args)
        if command == "vis-tree":
            return _cmd_vis_tree(args)
        if command == "vis-ast":
            return _cmd_vis_ast(args)
        if command == "vis-compare":
            return _cmd_vis_compare(args)
        raise CliInputError(f"Unknown command: {command}")
    except SiplSyntaxError as exc:
        return _emit_error(
            command=command,
            file_path=file_path,
            as_json=as_json,
            err_type=type(exc).__name__,
            message=str(exc),
            exit_code=EXIT_SYNTAX_ERROR,
            extra_error=exc.to_dict(),
        )
    except SiplRuntimeError as exc:
        return _emit_error(
            command=command,
            file_path=file_path,
            as_json=as_json,
            err_type=type(exc).__name__,
            message=str(exc),
            exit_code=EXIT_RUNTIME_ERROR,
            extra_error=exc.to_dict(),
        )
    except CliInputError as exc:
        return _emit_error(
            command=command,
            file_path=file_path,
            as_json=as_json,
            err_type=type(exc).__name__,
            message=str(exc),
            exit_code=EXIT_INPUT_ERROR,
        )


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()