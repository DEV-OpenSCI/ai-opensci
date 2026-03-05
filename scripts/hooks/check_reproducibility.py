#!/usr/bin/env python3
"""PostToolUse hook: check Python analysis scripts for reproducibility best practices.

Reads tool input from stdin (JSON). Checks if the written/edited file is a .py file
and warns if it lacks random seed settings or version logging.
"""

import json
import sys
import os


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".py"):
        return

    # Only check files in analysis/data/experiment directories
    analysis_keywords = ["analysis", "data", "experiment", "stats", "plot", "figure", "result"]
    path_lower = file_path.lower()
    if not any(kw in path_lower for kw in analysis_keywords):
        return

    # Read the file content
    content = ""
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        # For edits, read the file
        if os.path.exists(file_path):
            with open(file_path) as f:
                content = f.read()

    if not content:
        return

    warnings = []

    # Check for random seed
    if any(lib in content for lib in ["numpy", "random", "torch", "tensorflow", "sklearn"]):
        seed_patterns = ["random_seed", "random.seed", "np.random.seed", "torch.manual_seed",
                         "tf.random.set_seed", "PYTHONHASHSEED", "seed_everything"]
        if not any(p in content for p in seed_patterns):
            warnings.append("⚠️  No random seed found — results may not be reproducible")

    # Check for hardcoded file paths (should use relative or configurable)
    if "/Users/" in content or "C:\\" in content:
        warnings.append("⚠️  Hardcoded absolute path detected — use relative paths or config for portability")

    if warnings:
        print("\n".join(warnings), file=sys.stderr)


if __name__ == "__main__":
    main()
