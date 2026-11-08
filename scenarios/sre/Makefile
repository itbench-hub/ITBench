UV = $(shell which uv)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: group-vars
group-vars: ## Generates the group variables
	echo "---\nansible_python_interpreter: $(shell $(UV) python find)" > inventory/group_vars/all/python.yaml
	cp inventory/group_vars/all/storage.yaml.example inventory/group_vars/all/storage.yaml
	cp inventory/group_vars/orchestrator/agent.yaml.example inventory/group_vars/orchestrator/agent.yaml
	cp inventory/group_vars/orchestrator/experiments.yaml.example inventory/group_vars/orchestrator/experiments.yaml
	cp inventory/group_vars/orchestrator/github.yaml.example inventory/group_vars/orchestrator/github.yaml
	cp inventory/group_vars/orchestrator/stack.yaml.example inventory/group_vars/orchestrator/stack.yaml

.PHONY: test-molecule-faults
test-molecule-faults: ## Runs Molecule tests for the Faults role
	cd project/roles/faults && $(UV) run molecule test --all --report --command-borders

.PHONY: test-molecule-waiters
test-molecule-waiters: ## Runs Molecule tests for the Waiters role
	cd project/roles/waiters && $(UV) run molecule test --all --report --command-borders

# .PHONY: generate-agent-bundle
# generate-agent-bundle: ## Generates a bundle for an LLM Agent to interface with
# 	ANSIBLE_STDOUT_CALLBACK=ansible.posix.json $(UV) run ansible-playbook -i inventory project/generate_agent_bundle.yaml | jq -r '.plays[].tasks[] | select(.task.name == "Print agent bundle") | .hosts.localhost.msg'

# .PHONY: generate-leaderboard-bundle-status
# generate-leaderboard-bundle-status: ## Generates a bundle status for Leaderboard to interface with
# 	$(UV) run ansible-playbook -i inventory project/generate_leaderboard_bundle_status.yaml

# .PHONY: generate-leaderboard-bundle
# generate-leaderboard-bundle: ## Generates a bundle of scenarios for the Leaderboard to interface
# 	$(UV) run ansible-playbook -i inventory project/generate_leaderboard_bundle.yaml
