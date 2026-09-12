# ITBench Claude Configuration

This directory contains Claude Code skills, agents, and hooks to assist with ITBench scenario development.

Inspired by the [Langfuse .claude structure](https://github.com/langfuse/langfuse/tree/main/.claude).

## 📁 Structure

```
.claude/
├── agents/              # Complex, multi-step workflows
│   └── sre-scenario-creator.md
├── skills/              # Reusable knowledge blocks
│   ├── sre/             # SRE-specific skills
│   │   ├── fault-scaffolding/
│   │   │   └── SKILL.md
│   │   └── scenario-scaffolding/
│   │       └── SKILL.md
│   └── skill-rules.json
├── hooks/               # Automation scripts
│   └── skill-activation-prompt.sh
├── settings.json        # Project configuration
└── README.md           # This file
```

## 🎯 What This Enables

### Skills

**Skills are reusable instruction blocks** that auto-activate when working on specific tasks:

1. **`fault-scaffolding`** - Guides creating new faults from incident description to Ansible implementation
   - Auto-activates when editing `templates/library/indexes/faults/*.yaml.j2` or `inject_*.yaml` files
   - Provides patterns for JSON schemas, Ansible tasks, solutions
   - References existing fault implementations in `library/indexes/faults/`

2. **`scenario-scaffolding`** - Guides creating complete scenarios with ground truth
   - Auto-activates when editing `templates/library/indexes/scenarios/*.yaml.j2`
   - Guides disruption configuration and ground truth DSL generation
   - References existing groundtruth files in `library/specs/scenarios/`

### Agents

**Agents orchestrate complete workflows** from start to finish:

1. **`sre-scenario-creator`** - Full workflow for creating new scenarios
   - Step-by-step guidance from concept to validation
   - Integration with scaffold commands
   - Quality validation checklists

### Hooks

**Hooks automate suggestions** based on context:

1. **`skill-activation-prompt.sh`** - Auto-suggests relevant skills
   - Detects TODO patterns in files
   - Matches keywords in prompts
   - Suggests appropriate skills before responding

## 🚀 Quick Start

### Using Skills

Skills auto-activate based on context, but you can manually invoke them:

```bash
# After running make scaffold-fault
/skill fault-scaffolding

# After running make scaffold-scenario
/skill scenario-scaffolding
```

### Using Agents

Agents provide comprehensive workflows:

```bash
# For complete scenario creation
/agent sre-scenario-creator
```

Then describe what you want to create:
> "Create a new SRE scenario for pod eviction due to resource pressure"

### Complete Workflow Example

```bash
# 1. From the root directory, scaffold a new fault
make scaffold-fault
# Follow prompts (name, description, expectation)

# 2. Ask Claude to complete the fault index template
# The fault-scaffolding skill will auto-activate
> "Help me complete the fault template for excessive-memory-consumption"

# 3. Generate library outputs and Ansible role files
make generate-library
make validate-library
cd scenarios/sre && make generate-resource-files

# 4. From root, scaffold a new scenario
make scaffold-scenario

# 5. Ask Claude to complete the scenario template and ground truth
# The scenario-scaffolding skill will auto-activate
> "Help me complete the scenario using the excessive-memory-consumption fault"

# 6. Validate everything
make generate-library && make validate-library

# 7. Review generated documentation
cat documentation/library/faults/<fault-name>.md
cat documentation/library/scenarios/sre/<id>.md
```

## 📚 Skill Activation Patterns

Skills activate automatically when:

### Fault Scaffolding
- ✅ Editing `templates/library/indexes/faults/*.yaml.j2`
- ✅ Creating/editing `inject_*.yaml` files
- ✅ Prompt contains: "fault scaffold", "new fault", "complete fault"
- ✅ Prompt contains: "injection task", "fault arguments"

### Scenario Scaffolding
- ✅ Editing `templates/library/indexes/scenarios/*.yaml.j2`
- ✅ Editing `library/specs/scenarios/*/groundtruth*.yaml`
- ✅ Prompt contains: "scenario scaffold", "complete scenario"
- ✅ Prompt contains: "disruptions", "ground truth", "propagations"

## 🔧 Configuration

### Permissions

The `settings.json` allows:
- Bash commands: `find`, `grep`, `ls`, `cat`, `jq`
- Web fetching: GitHub and Kubernetes documentation
- All skills and agents in this directory

### Customization

#### Adding New Skills

1. Create directory: `.claude/skills/your-skill-name/`
2. Add `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: your-skill-name
   description: What this skill does
   ---
   ```
3. Add content with sections: Purpose, When to Use, Examples
4. Register in `skill-rules.json`:
   ```json
   {
     "name": "your-skill-name",
     "type": "suggest",
     "priority": "high",
     "triggers": {
       "prompt": {
         "keywords": ["keyword1", "keyword2"]
       },
       "file": {
         "pathPatterns": ["**/pattern/**"]
       }
     }
   }
   ```

#### Adding New Agents

1. Create file: `.claude/agents/your-agent-name.md`
2. Add YAML frontmatter:
   ```yaml
   ---
   name: your-agent-name
   description: Workflow description
   model: inherit
   color: blue
   ---
   ```
3. Structure with sections:
   - Role
   - Process (numbered steps)
   - Quality Standards
   - Output Format
   - Important Notes

## 🗂️ Key Paths Reference

| What | Where |
| --- | --- |
| Fault index templates | `templates/library/indexes/faults/<N>.yaml.j2` |
| Scenario index templates | `templates/library/indexes/scenarios/<N>.yaml.j2` |
| Rendered fault indexes | `library/indexes/faults/<N>.json` |
| Rendered scenario indexes | `library/indexes/scenarios/<N>.json` |
| Scenario specs (groundtruth, scenario.yaml) | `library/specs/scenarios/<ID>/` |
| Fault injection tasks | `scenarios/sre/project/roles/faults/tasks/inject_*.yaml` |
| Application releases (names + namespaces) | `scenarios/sre/project/roles/applications/vars/main/releases.yaml` |
| JSON schemas | `schemas/json/library/index/` |
| Generated documentation | `documentation/library/` |

## 🔑 Key Commands

| Command | Where | What it does |
| --- | --- | --- |
| `make scaffold-fault` | root | Create a new fault index template stub |
| `make scaffold-scenario` | root | Create a new scenario index template stub |
| `make generate-library` | root | Render templates → indexes, documentation, specs |
| `make validate-library` | root | Validate all indexes against JSON schemas |
| `make generate-resource-files` | `scenarios/sre/` | Generate Ansible role files from library indexes |

## 🐛 Troubleshooting

### Skills Not Activating

1. Check `skill-rules.json` syntax: `jq . .claude/skills/skill-rules.json`
2. Verify file patterns match: `ls templates/library/indexes/faults/*.yaml.j2`
3. Check hook is executable: `ls -la .claude/hooks/`
4. Review hook output: Check for skill suggestions in responses

### Hooks Not Running

1. Verify settings.json: `jq . .claude/settings.json`
2. Check hook permissions: `chmod +x .claude/hooks/*.sh`
3. Test hook manually: `echo '{"prompt":"fault scaffold"}' | .claude/hooks/skill-activation-prompt.sh`

### Validation Errors

1. Validate a fault index: `jq . library/indexes/faults/1.json`
2. Validate a scenario index: `jq . library/indexes/scenarios/1.json`
3. Run full validation: `make validate-library`
4. Check schema: `cat schemas/json/library/index/fault.json`

## 💡 Tips

- **Start with the agent** (`sre-scenario-creator`) for complete workflows
- **Use skills directly** when you just need quick patterns
- **Reference existing implementations** — search `library/indexes/faults/` before creating
- **Test in a cluster** — don't trust untested solutions
- **Commit incrementally** — fault template, then scenario template, then groundtruth

## 🤝 Contributing

When adding new skills or agents:

1. Follow the existing structure patterns
2. Include comprehensive examples
3. Add activation triggers to `skill-rules.json`
4. Test with real scaffolding workflows
5. Update this README with new capabilities

## 📝 Changelog

- **2026-02-20**: Initial structure created
  - Added fault-scaffolding skill
  - Added scenario-scaffolding skill
  - Added sre-scenario-creator agent
  - Added skill-activation hook
  - Configured permissions and settings
- **2025-07**: Updated for argo-refactor branch
  - Paths updated: library indexes now at `library/indexes/`, templates at `templates/library/indexes/`
  - Commands updated: `scaffold-fault`, `scaffold-scenario`, `generate-library`, `validate-library`, `generate-resource-files`
  - Application config moved to `scenarios/sre/project/roles/applications/vars/main/releases.yaml`
  - Groundtruth files now live in `library/specs/scenarios/<ID>/`
