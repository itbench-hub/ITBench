#!/bin/bash
# Skill Activation Hook for ITBench
# Auto-suggests relevant skills based on file context and user prompts

set -euo pipefail

# Read input from stdin
INPUT=$(cat)

# Extract prompt and current working directory
PROMPT=$(echo "$INPUT" | jq -r '.prompt // ""' | tr '[:upper:]' '[:lower:]')
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')

# Track activated skills
ACTIVATED_SKILLS=()

# Function to check if a file contains patterns
check_file_pattern() {
    local file="$1"
    local pattern="$2"

    if [ -f "$file" ]; then
        if grep -q "$pattern" "$file" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Check for fault-scaffolding activation
FAULT_INDEX="$CWD/scenarios/sre/roles/documentation/files/library/faults/index.json"
if [ -f "$FAULT_INDEX" ]; then
    # Check for TODO patterns in fault index
    if check_file_pattern "$FAULT_INDEX" '"alerts":\s*"TODO"' || \
       check_file_pattern "$FAULT_INDEX" '"arguments":\s*"TODO"' || \
       check_file_pattern "$FAULT_INDEX" '"resources":\s*"TODO"' || \
       check_file_pattern "$FAULT_INDEX" '"solutions":\s*"TODO"'; then
        ACTIVATED_SKILLS+=("fault-scaffolding")
    fi
fi

# Check for injection task TODOs
INJECTION_TASKS_DIR="$CWD/scenarios/sre/roles/faults/tasks"
if [ -d "$INJECTION_TASKS_DIR" ]; then
    if find "$INJECTION_TASKS_DIR" -name "inject_*.yaml" -exec grep -q "# TODO: LLM-generated injection task" {} \; 2>/dev/null; then
        if [[ ! " ${ACTIVATED_SKILLS[@]} " =~ " fault-scaffolding " ]]; then
            ACTIVATED_SKILLS+=("fault-scaffolding")
        fi
    fi
fi

# Check for scenario-scaffolding activation
SCENARIO_INDEX="$CWD/scenarios/sre/roles/documentation/files/library/scenarios/index.json"
if [ -f "$SCENARIO_INDEX" ]; then
    # Check for empty arrays or faultId hint
    if check_file_pattern "$SCENARIO_INDEX" '"faultId":' || \
       check_file_pattern "$SCENARIO_INDEX" '"disruptions":\s*\[\]' || \
       check_file_pattern "$SCENARIO_INDEX" '"solutions":\s*\[\]'; then
        ACTIVATED_SKILLS+=("scenario-scaffolding")
    fi
fi

# Check prompt keywords
if echo "$PROMPT" | grep -Eq "(fault|scenario).*(scaffold|todo|complete|fill)"; then
    if echo "$PROMPT" | grep -Eq "fault"; then
        if [[ ! " ${ACTIVATED_SKILLS[@]} " =~ " fault-scaffolding " ]]; then
            ACTIVATED_SKILLS+=("fault-scaffolding")
        fi
    fi
    if echo "$PROMPT" | grep -Eq "scenario"; then
        if [[ ! " ${ACTIVATED_SKILLS[@]} " =~ " scenario-scaffolding " ]]; then
            ACTIVATED_SKILLS+=("scenario-scaffolding")
        fi
    fi
fi

# Output activation suggestions
if [ ${#ACTIVATED_SKILLS[@]} -gt 0 ]; then
    echo ""
    echo "📚 **Relevant Skills Detected**"
    echo ""
    for skill in "${ACTIVATED_SKILLS[@]}"; do
        echo "   → **$skill**"
    done
    echo ""
    echo "**ACTION**: Consider using the Skill tool to load these skills for better assistance."
    echo ""
fi
