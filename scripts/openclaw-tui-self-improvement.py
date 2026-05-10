#!/usr/bin/env python3
"""TUI-focused self-improvement sidecar for the local OpenClaw harness.

This sidecar is deliberately observational by default. It checks the active
OpenClaw model profile, gateway/model reachability, memory pressure, and recent
runtime logs, then writes a compact report under ~/.openclaw/tui-self-improvement.
It never loads a model and never mutates live runtime configuration unless a
future command explicitly adds an apply gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MODEL_REF = "mlx/Gemma-4-31B-JANG_4M-CRACK"
DEFAULT_BASE_URL = "http://127.0.0.1:8091/v1"
DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789/health"
MAX_LOG_BYTES = 240_000

FAIL_PATTERNS = (
    re.compile(r"unknown model", re.I),
    re.compile(r"traceback|segmentation fault|bus error|metal.*error", re.I),
    re.compile(r"python.*crash|terminated due to memory", re.I),
)
WARN_PATTERNS = (
    re.compile(r"timeout|timed out|connection refused|watchdog", re.I),
    re.compile(r"memory pressure|compressor|swap", re.I),
    re.compile(r"\bthought(?:\s+thought){6,}\b", re.I),
    re.compile(r"tool_call.*malformed|malformed.*tool", re.I),
)


@dataclass
class Check:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def read_json(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def run(args: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception:
        return None


def http_ok(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= int(response.status) < 400, f"status={response.status}"
    except urllib.error.HTTPError as error:
        return False, f"http={error.code}"
    except Exception as error:
        return False, str(error)


def selected_model_ref(config: dict[str, Any]) -> str:
    try:
        value = config["agents"]["defaults"]["model"]["primary"]
    except Exception:
        return ""
    return value if isinstance(value, str) else ""


def model_entry(config: dict[str, Any], provider: str, model_id: str) -> dict[str, Any]:
    providers = config.get("models", {}).get("providers", {})
    provider_config = providers.get(provider, {}) if isinstance(providers, dict) else {}
    for item in provider_config.get("models", []):
        if isinstance(item, dict) and item.get("id") == model_id:
            return item
    return {}


def memory_snapshot() -> dict[str, Any]:
    result = run(["/usr/bin/vm_stat"], timeout=5)
    pressure = run(["/usr/bin/memory_pressure"], timeout=5)
    swap = run(["/usr/sbin/sysctl", "vm.swapusage"], timeout=5)
    page = 16384
    free = speculative = compressor = 0
    if result and result.stdout:
        for line in result.stdout.splitlines():
            if "page size of" in line:
                numbers = re.findall(r"\d+", line)
                if numbers:
                    page = int(numbers[-1])
            elif line.startswith("Pages free:"):
                free = int(re.sub(r"\D", "", line) or 0)
            elif line.startswith("Pages speculative:"):
                speculative = int(re.sub(r"\D", "", line) or 0)
            elif line.startswith("Pages occupied by compressor:"):
                compressor = int(re.sub(r"\D", "", line) or 0)
    pressure_free = None
    if pressure and pressure.stdout:
        match = re.search(r"System-wide memory free percentage:\s*(\d+)%", pressure.stdout)
        if match:
            pressure_free = int(match.group(1))
    swap_used = None
    if swap and swap.stdout:
        match = re.search(r"used = ([0-9.]+)M", swap.stdout)
        if match:
            swap_used = int(float(match.group(1)))
    return {
        "free_mb": int((free + speculative) * page / 1048576),
        "compressor_mb": int(compressor * page / 1048576),
        "pressure_free_pct": pressure_free,
        "swap_used_mb": swap_used,
    }


def memory_check(snapshot: dict[str, Any]) -> Check:
    free = int(snapshot.get("free_mb") or 0)
    compressor = int(snapshot.get("compressor_mb") or 0)
    swap = int(snapshot.get("swap_used_mb") or 0)
    pressure = snapshot.get("pressure_free_pct")
    detail = f"free={free}MB compressor={compressor}MB swap={swap}MB pressure_free={pressure}%"
    if free < 256 or compressor >= 32768:
        return Check("memory", "fail", detail)
    if free < 1024 or compressor >= 8192 or swap >= 8192:
        return Check("memory", "warn", detail)
    return Check("memory", "pass", detail)


def tail_text(path: Path, max_bytes: int = MAX_LOG_BYTES) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def scan_logs(log_dir: Path) -> tuple[Check, list[dict[str, str]]]:
    paths = [
        log_dir / "gateway.log",
        log_dir / "gateway.err.log",
        log_dir / "gateway-autostart.log",
        log_dir / "gateway-autostart.err.log",
        log_dir / "openclaw-model-proxy.log",
        log_dir / "openclaw-prefix-warmer.log",
        log_dir / "mlx-gemma-jang-server.log",
    ]
    findings: list[dict[str, str]] = []
    worst = "pass"
    for path in paths:
        text = tail_text(path)
        if not text:
            continue
        for pattern in FAIL_PATTERNS:
            match = pattern.search(text)
            if match:
                worst = "fail"
                findings.append({"file": str(path), "severity": "fail", "match": match.group(0)[:160]})
        for pattern in WARN_PATTERNS:
            match = pattern.search(text)
            if match:
                if worst != "fail":
                    worst = "warn"
                findings.append({"file": str(path), "severity": "warn", "match": match.group(0)[:160]})
    if not findings:
        return Check("recent_logs", "pass", "no known crash, loop, timeout, or tool-leak markers found"), findings
    fail_count = sum(1 for item in findings if item["severity"] == "fail")
    warn_count = sum(1 for item in findings if item["severity"] == "warn")
    return Check("recent_logs", worst, f"fail={fail_count} warn={warn_count}"), findings[-12:]


def build_report(openclaw_dir: Path, gateway_url: str) -> dict[str, Any]:
    config_path = openclaw_dir / "openclaw.json"
    profiles_path = openclaw_dir / "model-profiles.json"
    config = read_json(config_path, {})
    profiles = read_json(profiles_path, {})
    checks: list[Check] = []

    primary = selected_model_ref(config)
    checks.append(
        Check(
            "selected_model",
            "pass" if primary == DEFAULT_MODEL_REF else "warn",
            primary or "missing primary model",
        )
    )

    profile = profiles.get("profiles", {}).get(primary, {}) if isinstance(profiles, dict) else {}
    checks.append(
        Check(
            "model_profile",
            "pass" if profile else "fail",
            f"profile found for {primary}" if profile else f"missing profile for {primary}",
        )
    )

    provider = primary.split("/", 1)[0] if "/" in primary else ""
    model_id = profile.get("model") if isinstance(profile, dict) else ""
    model = model_entry(config, provider, str(model_id))
    provider_config = config.get("models", {}).get("providers", {}).get(provider, {}) if isinstance(config, dict) else {}
    base_url = provider_config.get("baseUrl") if isinstance(provider_config, dict) else ""
    checks.append(
        Check(
            "base_url",
            "pass" if base_url == DEFAULT_BASE_URL else "warn",
            str(base_url or "missing"),
        )
    )
    checks.append(
        Check(
            "reasoning",
            "pass" if model.get("reasoning") is True else "warn",
            f"reasoning={model.get('reasoning')!r}",
        )
    )

    health_url = str(profile.get("healthUrl") or DEFAULT_BASE_URL + "/models")
    model_ok, model_detail = http_ok(health_url)
    checks.append(Check("model_api", "pass" if model_ok else "warn", f"{health_url} {model_detail}"))
    gateway_ok, gateway_detail = http_ok(gateway_url)
    checks.append(Check("gateway", "pass" if gateway_ok else "warn", f"{gateway_url} {gateway_detail}"))

    memory = memory_snapshot()
    checks.append(memory_check(memory))
    log_check, log_findings = scan_logs(openclaw_dir / "logs")
    checks.append(log_check)

    status_order = {"pass": 0, "warn": 1, "fail": 2}
    worst = max(checks, key=lambda item: status_order[item.status]).status
    report = {
        "created_at": now(),
        "ok": worst != "fail",
        "severity": worst,
        "model_ref": primary,
        "memory": memory,
        "checks": [check.to_dict() for check in checks],
        "log_findings": log_findings,
        "recommendation": recommendation(checks),
    }
    return report


def recommendation(checks: list[Check]) -> str:
    failures = [check for check in checks if check.status == "fail"]
    warnings = [check for check in checks if check.status == "warn"]
    if failures:
        names = ", ".join(check.name for check in failures)
        return f"Fix blocking harness drift before starting a long TUI run: {names}."
    if any(check.name == "memory" and check.status == "warn" for check in warnings):
        return "Memory is warm or compressed; avoid starting a second large local model."
    if any(check.name in {"model_api", "gateway"} for check in warnings):
        return "Runtime is not fully warm; wrapper startup should start the missing service before TUI use."
    if warnings:
        names = ", ".join(check.name for check in warnings)
        return f"Harness is usable, with non-blocking warnings: {names}."
    return "Harness checks are clean."


def print_human(report: dict[str, Any]) -> None:
    print(f"OpenClaw TUI self-improvement: {report['severity']} - {report['recommendation']}")
    for check in report["checks"]:
        print(f"- {check['status']:4} {check['name']}: {check['detail']}")
    report_path = report.get("report_path")
    if report_path:
        print(f"Report: {report_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review OpenClaw TUI harness health without mutating runtime state.")
    parser.add_argument("command", nargs="?", choices=("review", "health", "doctor"), default="review")
    parser.add_argument("--openclaw-dir", type=Path, default=Path.home() / ".openclaw")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args.openclaw_dir.expanduser(), args.gateway_url)
    reports_dir = args.openclaw_dir.expanduser() / "tui-self-improvement" / "reports"
    report_path = reports_dir / f"tui-health-{time.strftime('%Y%m%d-%H%M%S')}.json"
    report["report_path"] = str(report_path)
    write_json(report_path, report)
    append_jsonl(args.openclaw_dir.expanduser() / "tui-self-improvement" / "journal.jsonl", report)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif not args.quiet:
        print_human(report)

    if args.fail_on_critical and report["severity"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
