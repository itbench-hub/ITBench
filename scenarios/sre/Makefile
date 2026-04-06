# Makefile to run Ansible project

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: group-vars
group-vars: ## Generates the group variables
	echo "---\nansible_python_interpreter: $(shell uv python find)" > inventory/group_vars/all/python.yaml
	cp inventory/group_vars/all/storage.yaml.example inventory/group_vars/all/storage.yaml
	cp inventory/group_vars/environment/applications.yaml.example inventory/group_vars/environment/applications.yaml
	cp inventory/group_vars/environment/cluster.yaml.example inventory/group_vars/environment/cluster.yaml
	cp inventory/group_vars/environment/tools.yaml.example inventory/group_vars/environment/tools.yaml
	cp inventory/group_vars/runner/agent.yaml.example inventory/group_vars/runner/agent.yaml
	cp inventory/group_vars/runner/credentials.yaml.example inventory/group_vars/runner/credentials.yaml
	cp inventory/group_vars/runner/experiments.yaml.example inventory/group_vars/runner/experiments.yaml
	cp inventory/group_vars/runner/github.yaml.example inventory/group_vars/runner/github.yaml
	cp inventory/group_vars/runner/stack.yaml.example inventory/group_vars/runner/stack.yaml

.PHONY: generate-docs
generate-docs: ## Generates library indexes, schemas, and other related documentation
	uv run ansible-playbook -i inventory project/manage_documentation.yaml --tags "generate_docs"

.PHONY: scaffold-fault
scaffold-fault: ## Collect user input and create skeleton for fault entry
	uv run ansible-playbook -i inventory.yaml playbooks/scaffold_fault.yaml
	uv run ansible-lint roles/scenarios/files roles/scenarios/meta roles/waiters/meta roles/faults/meta --fix

.PHONY: scaffold-scenario
scaffold-scenario: ## Collect user input and create skeleton for scenario entry
	uv run ansible-playbook -i inventory.yaml playbooks/scaffold_scenario.yaml
	uv run ansible-lint roles/scenarios/files roles/scenarios/meta roles/waiters/meta roles/faults/meta --fix

.PHONY: validate-docs
validate-docs: ## Validates library indexes
	uv run ansible-playbook -i inventory project/manage_documentation.yaml --tags "validate_docs"

.PHONY: generate-scenario-files
generate-scenario-files: ## Generates scenario related files using library indexes
	uv run ansible-playbook -i inventory project/generate_scenario_files.yaml --tags "generate_files"
	cd ../../ && uv run ansible-lint project/roles/scenarios/files project/roles/scenarios/meta project/roles/waiters/meta project/roles/faults/meta --fix

.PHONY: regenerate-scenario-files
regenerate-scenario-files: ## Overwrites scenario related files using library indexes
	uv run ansible-playbook -i inventory project/generate_scenario_files.yaml --tags "generate_files" \
		--extra-vars "overwrite_files=true"
	cd ../../ && uv run ansible-lint project/roles/scenarios/files project/roles/scenarios/meta project/roles/waiters/meta project/roles/faults/meta --fix

.PHONY: deploy-tools
deploy-tools: ## Deploys the observability and fault tools to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory project/manage_tools.yaml --tags "install_tools" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory project/manage_tools.yaml --tags "install_tools"
endif

.PHONY: undeploy-tools
undeploy-tools: ## Undeploys the observability and fault tools from cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory project/manage_tools.yaml --tags "uninstall_tools" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory project/manage_tools.yaml --tags "uninstall_tools"
endif

.PHONY: deploy-applications
deploy-applications: ## Deploys the applications to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory project/manage_applications.yaml --tags "install_applications" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory project/manage_applications.yaml --tags "install_applications"
endif

.PHONY: undeploy-applications
undeploy-applications: ## Undeploys the applications to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory project/manage_applications.yaml --tags "uninstall_applications" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory project/manage_applications.yaml --tags "uninstall_applications"
endif

.PHONY: deploy-recorders
deploy-recorders: ## Deploys the data recorders to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory project/manage_recorders.yaml --tags "install_recorders" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory project/manage_recorders.yaml --tags "install_recorders"
endif

.PHONY: undeploy-recorders
undeploy-recorders: ## Undeploys the data recorders to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory project/manage_recorders.yaml --tags "uninstall_recorders" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory project/manage_recorders.yaml --tags "uninstall_recorders"
endif

.PHONY: inject-scenario-faults
inject-scenario-faults: ## Injects the fault used in a specific scenario
ifdef SCENARIO_NUMBER
	$(shell uv python find) scripts/inject_scenario_faults.py \
		--private_project_directory $(shell pwd) \
		--scenario_id $(SCENARIO_NUMBER)
else
	@echo "Missing SCENARIO_NUMBER argument. Please run this command with this variable."
endif

.PHONY: remove-fault-resources
remove-fault-resources: ## Removes resources used during fault injection
	uv run ansible-playbook -i inventory project/manage_faults.yaml --tags "remove_faults"

.PHONY: create-environment
create-environment: deploy-tools deploy-applications ## Deploys tools and applications to cluster

.PHONY: destroy-environment
destroy-environment: undeploy-applications undeploy-tools ## Undeploys tools and applications to cluster

.PHONY: start-incident
start-incident: create-environment deploy-recorders inject-scenario-faults ## Starts an incident by deploying a stack, applications, faults, and recorders for an incident

.PHONY: stop-incident
stop-incident: undeploy-recorders remove-fault-resources destroy-environment ## Stops an incident by undeploying a stack, applications, faults, and recorders for an incident

.PHONY: enable-agent-access
enable-agent-access: ## Adds access controls for llm agent
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory project/manage_agent_access.yaml --tags "grant_access" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	@echo "Missing SCENARIO_NUMBER argument. Please run this command with this variable."
endif

.PHONY: disable-agent-access
disable-agent-access: ## Removes access controls for llm agent
	uv run ansible-playbook -i inventory project/manage_agent_access.yaml --tags "revoke_access"

.PHONY: test-unit-agent
test-unit-agent: ## Runs agent access unit tests
	cd project/roles/agent && uv run molecule test --all --report --command-borders

.PHONY: test-unit-faults
test-unit-faults: ## Runs fault injection unit tests
	cd project/roles/faults && uv run molecule test --all --report --command-borders

.PHONY: test-unit-recorders
test-unit-recorders: ## Runs recorder installation unit tests
	cd project/roles/recorders && uv run molecule test --all --report --command-borders

.PHONY: test-unit-tools
test-unit-tools: ## Runs tool installation unit tests
	cd project/roles/tools && uv run molecule test --all --report --command-borders

.PHONY: test-unit-waiters
test-unit-waiters: ## Runs waiter unit tests
	cd project/roles/waiters && uv run molecule test --all --report --command-borders

.PHONY: generate-agent-bundle
generate-agent-bundle: ## Generates a bundle for an LLM Agent to interface with
	ANSIBLE_STDOUT_CALLBACK=ansible.posix.json uv run ansible-playbook -i inventory project/generate_agent_bundle.yaml | jq -r '.plays[].tasks[] | select(.task.name == "Print agent bundle") | .hosts.localhost.msg'

.PHONY: generate-leaderboard-bundle-status
generate-leaderboard-bundle-status: ## Generates a bundle status for Leaderboard to interface with
	uv run ansible-playbook -i inventory project/generate_leaderboard_bundle_status.yaml

.PHONY: generate-leaderboard-bundle
generate-leaderboard-bundle: ## Generates a bundle of scenarios for the Leaderboard to interface
	uv run ansible-playbook -i inventory project/generate_leaderboard_bundle.yaml
