#!/usr/bin/env python3
"""Pipeline stage timer — 记录每个阶段的开始/结束时间，生成用时统计报告"""

import json
import os
import sys
import time
from datetime import datetime

TIMER_FILE = os.path.expanduser("~/.cache/ai-opensci/pipeline_timer.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(TIMER_FILE), exist_ok=True)


def _load():
    if os.path.exists(TIMER_FILE):
        with open(TIMER_FILE) as f:
            return json.load(f)
    return {"stages": [], "pipeline_start": None}


def _save(data):
    _ensure_dir()
    with open(TIMER_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def start_pipeline():
    """Reset and start a new pipeline timer."""
    data = {"stages": [], "pipeline_start": time.time()}
    _save(data)
    print(f"⏱ Pipeline started at {datetime.now().strftime('%H:%M:%S')}")


def start_stage(name: str):
    """Mark the start of a stage."""
    data = _load()
    # End previous stage if still running
    for stage in data["stages"]:
        if stage.get("end") is None:
            stage["end"] = time.time()
            stage["duration"] = stage["end"] - stage["start"]

    data["stages"].append({
        "name": name,
        "start": time.time(),
        "end": None,
        "duration": None,
    })
    _save(data)
    print(f"⏱ Stage [{name}] started at {datetime.now().strftime('%H:%M:%S')}")


def end_stage(name: str = ""):
    """Mark the end of the current (or named) stage."""
    data = _load()
    for stage in reversed(data["stages"]):
        if stage.get("end") is None and (not name or stage["name"] == name):
            stage["end"] = time.time()
            stage["duration"] = stage["end"] - stage["start"]
            _save(data)
            print(f"✅ Stage [{stage['name']}] completed in {_format_duration(stage['duration'])}")
            return
    print("⚠ No active stage to end")


def report():
    """Print the full timing report."""
    data = _load()
    now = time.time()

    # Close any unclosed stages
    for stage in data["stages"]:
        if stage.get("end") is None:
            stage["end"] = now
            stage["duration"] = stage["end"] - stage["start"]

    total = now - data["pipeline_start"] if data.get("pipeline_start") else 0
    stages = data.get("stages", [])

    if not stages:
        print("No stages recorded.")
        return

    # Find max name length for alignment
    max_name = max(len(s["name"]) for s in stages)
    max_dur = max(s["duration"] for s in stages) if stages else 1

    print()
    print("=" * 60)
    print("  PIPELINE TIMING REPORT")
    print("=" * 60)
    print()

    for i, s in enumerate(stages, 1):
        dur = s["duration"]
        bar_len = int((dur / max_dur) * 30) if max_dur > 0 else 0
        bar = "█" * bar_len + "░" * (30 - bar_len)
        pct = (dur / total * 100) if total > 0 else 0
        print(f"  {i}. {s['name']:<{max_name}}  {bar}  {_format_duration(dur):>8}  ({pct:.0f}%)")

    print()
    print(f"  {'TOTAL':<{max_name}}  {'':>30}  {_format_duration(total):>8}  (100%)")
    print()
    print("=" * 60)

    # Also output as markdown table
    print()
    print("| # | Stage | Duration | % |")
    print("|---|-------|----------|---|")
    for i, s in enumerate(stages, 1):
        dur = s["duration"]
        pct = (dur / total * 100) if total > 0 else 0
        print(f"| {i} | {s['name']} | {_format_duration(dur)} | {pct:.0f}% |")
    print(f"| | **Total** | **{_format_duration(total)}** | **100%** |")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: timer.py <start-pipeline|start|end|report> [stage_name]")
        sys.exit(1)

    cmd = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else ""

    if cmd == "start-pipeline":
        start_pipeline()
    elif cmd == "start":
        start_stage(name)
    elif cmd == "end":
        end_stage(name)
    elif cmd == "report":
        report()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
