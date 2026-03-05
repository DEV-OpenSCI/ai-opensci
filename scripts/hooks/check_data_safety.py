#!/usr/bin/env python3
"""PreToolUse hook: warn when writing files that may contain sensitive research data.

Reads tool input from stdin (JSON). Checks file extensions and content patterns
for potentially sensitive data (patient IDs, emails, etc.).
"""

import json
import sys


SENSITIVE_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet", ".hdf5", ".h5"}

SENSITIVE_PATTERNS = [
    "patient_id", "patient_name", "ssn", "social_security",
    "date_of_birth", "dob", "medical_record", "mrn",
    "email", "phone_number", "address", "zip_code",
    "credit_card", "api_key", "password", "secret",
]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    # Check extension
    ext = ""
    for e in SENSITIVE_EXTENSIONS:
        if file_path.endswith(e):
            ext = e
            break

    warnings = []

    # Check content for sensitive patterns
    if content:
        content_lower = content.lower()
        found = [p for p in SENSITIVE_PATTERNS if p in content_lower]
        if found:
            warnings.append(
                f"⚠️  Potentially sensitive fields detected: {', '.join(found[:5])}\n"
                f"   Ensure this data is properly anonymized before sharing."
            )

    if warnings:
        print("\n".join(warnings), file=sys.stderr)


if __name__ == "__main__":
    main()
