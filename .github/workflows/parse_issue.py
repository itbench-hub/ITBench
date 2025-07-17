import json
import re
import sys


def parse_issue_body(issue_body: str):
    result = {}
    sections = re.split(r"^###\s+", issue_body, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().splitlines()
        if not lines:
            continue
        key = lines[0].strip()
        value_lines = lines[1:]

        if not value_lines:
            result[key] = ""
            continue

        value_lines = [x for x in value_lines if x != '']
        if all(re.match(r"^- \[[ xX]\] ", line) for line in value_lines):
            options = {}
            for line in value_lines:
                match = re.match(r"^- \[([ xX])\] (.+)", line)
                if match:
                    checked = match.group(1).lower() == 'x'
                    label = match.group(2).strip()
                    options[label] = checked
            result[key] = options
        else:
            value = "\n".join(value_lines).strip()
            result[key] = value

    print(json.dumps(result))

if __name__ == "__main__":
    issue_body = sys.stdin.read()
    parse_issue_body(issue_body)
