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
│   │   ├── scenario-scaffolding/
│   │   │   └── SKILL.md
│   │   └── trial-verifier/
│   │       ├── SKILL.md
│   │       └── trial_verifier_service_aware.py
│   └── skill-rules.json
├── hooks/               # Automation scripts
│   └── skill-activation-prompt.sh
├── settings.json        # Project configuration
└── README.md           # This file
```

## 🎯 What This Enables

### Skills

**Skills are reusable instruction blocks** that auto-activate when working on specific tasks:

1. **`fault-scaffolding`** - Helps complete fault TODO fields
   - Auto-activates when editing `faults/index.json` or `inject_*.yaml` files
   - Provides patterns for JSON schemas, Ansible tasks, solutions
   - References existing fault implementations

2. **`scenario-scaffolding`** - Helps complete scenario TODO fields
   - Auto-activates when editing `scenarios/index.json`
   - Guides disruption configuration
   - Adapts fault solutions to scenarios

### Agents

**Agents orchestrate complete workflows** from start to finish:

1. **`sre-scenario-creator`** - Full workflow for creating new scenarios
   - Step-by-step guidance from concept to documentation
   - Integration with scaffolding commands
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
# After running scaffold_fault
/skill fault-scaffolding

# After running scaffold_scenario
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
# 1. Start in the SRE scenarios directory
cd scenarios/sre

# 2. Scaffold a new fault
make scaffold_fault
# Follow prompts...

# 3. Ask Claude to complete the TODOs
# The fault-scaffolding skill will auto-activate
> "Help me complete the fault TODOs for excessive-memory-consumption"

# 4. Scaffold a scenario using that fault
make scaffold_scenario
# Select the fault you just created...

# 5. Ask Claude to complete the scenario
# The scenario-scaffolding skill will auto-activate
> "Help me complete the scenario using the excessive-memory-consumption fault"

# 6. Generate documentation
make regenerate-scenario-files

# 7. Review the results
cat docs/faults.md | grep -A 30 "Excessive Memory Consumption"
cat docs/scenarios.md | grep -A 50 "Scenario [ID]"
```

## 📚 Skill Activation Patterns

Skills activate automatically when:

### Fault Scaffolding
- ✅ Editing `faults/index.json` with TODO patterns
- ✅ Creating/editing `inject_*.yaml` files
- ✅ Prompt contains: "fault scaffold", "complete fault", "fill fault"
- ✅ Prompt contains: "injection task", "fault arguments"

### Scenario Scaffolding
- ✅ Editing `scenarios/index.json` with empty arrays
- ✅ Files contain `"faultId":` scaffolding hint
- ✅ Prompt contains: "scenario scaffold", "complete scenario"
- ✅ Prompt contains: "disruptions", "scenario solutions"

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

## 🎓 Learning Resources

### Understanding the Structure

- **Skills** → Documentation-driven, context-aware assistance
- **Agents** → Workflow orchestration with quality gates
- **Hooks** → Automated suggestions and tracking

### Best Practices

1. **Skills should be modular** - Focus on one domain
2. **Agents should be comprehensive** - Cover full workflows
3. **Hooks should be lightweight** - Fast pattern matching
4. **Always include examples** - Show, don't just tell
5. **Reference existing code** - Link to real implementations

### References

- [Langfuse .claude structure](https://github.com/langfuse/langfuse/tree/main/.claude) - Original inspiration
- [OpenCode.ai Skills Docs](https://opencode.ai/docs/skills/) - Official documentation
- [ITBench Developer Guide](../../scenarios/sre/DEVELOPER_GUIDE.md) - Project context
- [Faults Documentation](../../scenarios/sre/docs/faults.md) - Fault reference
- [Scenarios Documentation](../../scenarios/sre/docs/scenarios.md) - Scenario reference

## 🐛 Troubleshooting

### Skills Not Activating

1. Check `skill-rules.json` syntax: `jq . .claude/skills/skill-rules.json`
2. Verify file patterns match: `ls -la scenarios/sre/roles/documentation/files/library/faults/index.json`
3. Check hook is executable: `ls -la .claude/hooks/`
4. Review hook output: Check for skill suggestions in responses

### Hooks Not Running

1. Verify settings.json: `jq . .claude/settings.json`
2. Check hook permissions: `chmod +x .claude/hooks/*.sh`
3. Test hook manually: `echo '{"prompt":"fault scaffold"}' | .claude/hooks/skill-activation-prompt.sh`

### JSON Validation Errors

1. Validate faults index: `jq . scenarios/sre/roles/documentation/files/library/faults/index.json`
2. Validate scenarios index: `jq . scenarios/sre/roles/documentation/files/library/scenarios/index.json`
3. Run linter: `cd scenarios/sre && make lint`

## 💡 Tips

- **Start with the agent** (`sre-scenario-creator`) for complete workflows
- **Use skills directly** when you just need quick patterns
- **Reference existing implementations** - Search before creating
- **Test in a cluster** - Don't trust untested solutions
- **Commit incrementally** - Fault, then scenario, then docs

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
