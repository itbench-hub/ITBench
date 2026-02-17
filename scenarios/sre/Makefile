# Makefile to run Ansible playbooks

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: deps
deps: ## Installs dependencies
	uv sync
	uv run ansible-galaxy install -r requirements.yaml --force

.PHONY: pre-commit-hooks
pre-commit-hooks: ## Installs pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg --hook-type pre-push

.PHONY: group-vars
group-vars: ## Generates the group variables
	echo "ansible_python_interpreter: $(shell uv python find)" > group_vars/all/ansible.yaml
	cp group_vars/all/storage.yaml.example group_vars/all/storage.yaml
	cp group_vars/environment/applications.yaml.example group_vars/environment/applications.yaml
	cp group_vars/environment/cluster.yaml.example group_vars/environment/cluster.yaml
	cp group_vars/environment/tools.yaml.example group_vars/environment/tools.yaml

.PHONY: generate-docs
generate-docs: ## Generates library indexes, schemas, and other related documentation
	uv run ansible-playbook -i inventory.yaml playbooks/manage_documentation.yaml --tags "generate_docs"

.PHONY: validate-docs
validate-docs: ## Validates library indexes
	uv run ansible-playbook -i inventory.yaml playbooks/manage_documentation.yaml --tags "validate_docs"

.PHONY: generate-scenario-files
generate-scenario-files: ## Generates scenario related files using library indexes
	uv run ansible-playbook -i inventory.yaml playbooks/generate_scenario_files.yaml --tags "generate_files"
	uv run ansible-lint roles/scenarios/files roles/scenarios/meta roles/waiters/meta roles/faults/meta --fix

.PHONY: regenerate-scenario-files
regenerate-scenario-files: ## Overwrites scenario related files using library indexes
	uv run ansible-playbook -i inventory.yaml playbooks/generate_scenario_files.yaml --tags "generate_files" \
		--extra-vars "overwrite_files=true"
	uv run ansible-lint roles/scenarios/files roles/scenarios/meta roles/waiters/meta roles/faults/meta --fix

.PHONY: deploy-tools
deploy-tools: ## Deploys the observability and fault tools to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "install_tools" \
		--extra-vars "incident_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "install_tools"
endif

.PHONY: undeploy-tools
undeploy-tools: ## Undeploys the observability and fault tools from cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "uninstall_tools" \
		--extra-vars "incident_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "uninstall_tools"
endif

.PHONY: remove-tools-crds
remove-tools-crds: ## Removes all the observability and fault tools custom resource definitions from cluster
	uv run ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "uninstall_tools" \
		--extra-vars "remove_crds=true"

.PHONY: deploy_applications
deploy_applications: ## Deploys the applications to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "install_applications" \
		--extra-vars "incident_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "install_applications"
endif

.PHONY: undeploy_applications
undeploy_applications: ## Undeploys the applications to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "uninstall_applications" \
		--extra-vars "incident_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "uninstall_applications"
endif

.PHONY: deploy-recorders
deploy-recorders: ## Deploys the data recorders to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "install_recorders" \
		--extra-vars "incident_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "install_recorders"
endif

.PHONY: undeploy-recorders
undeploy-recorders: ## Undeploys the data recorders to cluster
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "uninstall_recorders" \
		--extra-vars "incident_id=$(SCENARIO_NUMBER)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "uninstall_recorders"
endif

.PHONY: inject-scenario-faults
inject-scenario-faults: ## Injects the fault used in a specific scenario
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_faults.yaml --tags "inject_faults" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	@echo "Missing SCENARIO_NUMBER argument. Please run this command with this variable."
endif

.PHONY: remove-fault-resources
remove-fault-resources: ## Removes resources used during fault injection
ifdef SCENARIO_NUMBER
	uv run ansible-playbook -i inventory.yaml playbooks/manage_faults.yaml --tags "remove_faults" \
		--extra-vars "scenario_id=$(SCENARIO_NUMBER)"
else
	@echo "Missing SCENARIO_NUMBER argument. Please run this command with this variable."
endif

.PHONY: create-environment
create-environment: deploy-tools deploy-applications ## Deploys tools and applications to cluster

.PHONY: destroy-environment
destroy-environment: undeploy-applications undeploy-tools ## Undeploys tools and applications to cluster

.PHONY: start-incident
start-incident: create-environment deploy-recorders inject-scenario-faults ## Starts an incident by deploying a stack, applications, faults, and recorders for an incident

.PHONY: stop-incident
stop-incident: undeploy-recorders remove-fault-resources destroy-environment ## Stops an incident by undeploying a stack, applications, faults, and recorders for an incident

.PHONY: test-unit-faults
test-unit-faults: ## Runs fault injection unit tests
	cd roles/faults && uv run molecule test --all --report --command-borders

.PHONY: test-unit-waiters
test-unit-waiters: ## Runs waiter unit tests
	cd roles/waiters && uv run molecule test --all --report --command-borders

.PHONY: enable-agent-access
enable-agent-access: ## Adds access controls for llm agent
	uv run ansible-playbook -i inventory.yaml playbooks/manage_agent_access.yaml --tags "grant_access"

.PHONY: disable-agent-access
disable-agent-access: ## Removes access controls for llm agent
	uv run ansible-playbook -i inventory.yaml playbooks/manage_agent_access.yaml --tags "revoke_access"

.PHONY: generate-agent-bundle
generate-agent-bundle: ## Generates a bundle for an LLM Agent to interface with
	ANSIBLE_STDOUT_CALLBACK=ansible.posix.json uv run ansible-playbook -i inventory.yaml playbooks/generate_agent_bundle.yaml | jq -r '.plays[].tasks[] | select(.task.name == "Print agent bundle") | .hosts.localhost.msg'

.PHONY: generate-leaderboard-bundle-status
generate-leaderboard-bundle-status: ## Generates a bundle status for Leaderboard to interface with
	uv run ansible-playbook -i inventory.yaml playbooks/generate_leaderboard_bundle_status.yaml

.PHONY: generate-leaderboard-bundle
generate-leaderboard-bundle: ## Generates a bundle of scenarios for the Leaderboard to interface
	uv run ansible-playbook -i inventory.yaml playbooks/generate_leaderboard_bundle.yaml

PHONY: fetch-alerts
fetch-alerts: ## Checks the Prometheus for firing alerts
	ansible-runner run ./ -p check_for_specific_alerts_in_firing_state.yaml
