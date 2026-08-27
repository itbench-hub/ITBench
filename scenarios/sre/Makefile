UV = $(shell which uv)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: group-vars
group-vars: ## Generates the group variables
	echo "---\nansible_python_interpreter: $(shell $(UV) python find)" > inventory/group_vars/all/python.yaml
	cp inventory/group_vars/all/storage.yaml.example inventory/group_vars/all/storage.yaml
	cp inventory/group_vars/environment/applications.yaml.example inventory/group_vars/environment/applications.yaml
	cp inventory/group_vars/environment/cluster.yaml.example inventory/group_vars/environment/cluster.yaml
	cp inventory/group_vars/environment/tools.yaml.example inventory/group_vars/environment/tools.yaml
	cp inventory/group_vars/runner/agent.yaml.example inventory/group_vars/runner/agent.yaml
	cp inventory/group_vars/runner/experiments.yaml.example inventory/group_vars/runner/experiments.yaml
	cp inventory/group_vars/runner/github.yaml.example inventory/group_vars/runner/github.yaml
	cp inventory/group_vars/runner/stack.yaml.example inventory/group_vars/runner/stack.yaml

.PHONY: generate-fault-index
generate-fault-index: ## Generate a new fault index based on user input
	$(UV) run ansible-playbook -i inventory.yaml project/generate_documentation_index.yaml --tags "generate_fault"

.PHONY: generate-scenario-index
generate-scenario-index: ## Generate a new scenario index based on user input
	$(UV) run ansible-playbook -i inventory.yaml project/generate_documentation_index.yaml --tags "generate_scenario"

.PHONY: generate-resource-files
generate-resource-files: ## Generates task files, scenario manifests, and other related files
	$(UV) run ansible-playbook -i inventory project/manage_resource_files.yaml --tags "generate_files"
	cd ../../ && $(UV) run ansible-lint $(abspath project/roles/scenarios/files) --fix

.PHONY: deploy-tools
deploy-tools: ## Deploys the observability and fault tools to cluster
ifdef SCENARIO_NUMBER
	$(UV) run ansible-playbook -i inventory project/manage_tools.yaml --tags "install_tools" \
		--extra-vars "scenario_specs_directory=$(abspath ../../../library/specs/scenarios/$(SCENARIO_NUMBER))"
else
	$(UV) run ansible-playbook -i inventory project/manage_tools.yaml --tags "install_tools"
endif

.PHONY: display-endpoints
display-endpoints: ## Shows the urls for accessing deployed tools in browser
	$(UV) run ansible-playbook -i inventory project/display_gateway_endpoints.yaml

.PHONY: undeploy-tools
undeploy-tools: ## Undeploys the observability and fault tools from cluster
ifdef SCENARIO_NUMBER
	$(UV) run ansible-playbook -i inventory project/manage_tools.yaml --tags "uninstall_tools" \
		--extra-vars "scenario_specs_directory=$(abspath ../../../library/specs/scenarios/$(SCENARIO_NUMBER))"
else
	$(UV) run ansible-playbook -i inventory project/manage_tools.yaml --tags "uninstall_tools"
endif

.PHONY: deploy-applications
deploy-applications: ## Deploys the applications to cluster
ifdef SCENARIO_NUMBER
	$(UV) run ansible-playbook -i inventory project/manage_applications.yaml --tags "install_applications" \
		--extra-vars "scenario_specs_directory=$(abspath ../../../library/specs/scenarios/$(SCENARIO_NUMBER))"
else
	$(UV) run ansible-playbook -i inventory project/manage_applications.yaml --tags "install_applications"
endif

.PHONY: undeploy-applications
undeploy-applications: ## Undeploys the applications to cluster
ifdef SCENARIO_NUMBER
	$(UV) run ansible-playbook -i inventory project/manage_applications.yaml --tags "uninstall_applications" \
		--extra-vars "scenario_specs_directory=$(abspath ../../../library/specs/scenarios/$(SCENARIO_NUMBER))"
else
	$(UV) run ansible-playbook -i inventory project/manage_applications.yaml --tags "uninstall_applications"
endif

.PHONY: deploy-recorders
deploy-recorders: ## Deploys the data recorders to cluster
ifdef SCENARIO_NUMBER
	$(UV) run ansible-playbook -i inventory project/manage_recorders.yaml --tags "install_recorders" \
		--extra-vars "scenario_specs_directory=$(abspath ../../../library/specs/scenarios/$(SCENARIO_NUMBER))"
else
	$(UV) run ansible-playbook -i inventory project/manage_recorders.yaml --tags "install_recorders"
endif

.PHONY: undeploy-recorders
undeploy-recorders: ## Undeploys the data recorders to cluster
	$(UV) run ansible-playbook -i inventory project/manage_recorders.yaml --tags "uninstall_recorders"

.PHONY: inject-scenario-faults
inject-scenario-faults: ## Injects the fault used in a specific scenario
ifdef SCENARIO_NUMBER
	$(UV) run scripts/inject_scenario_faults.py \
		--private_project_directory $(abspath .) \
		--scenario_id $(SCENARIO_NUMBER)
else
	@echo "Missing SCENARIO_NUMBER argument. Please run this command with this variable."
endif

.PHONY: remove-fault-resources
remove-fault-resources: ## Removes resources used during fault injection
	$(UV) run ansible-playbook -i inventory project/manage_faults.yaml --tags "remove_faults"

.PHONY: create-environment
create-environment: deploy-tools deploy-applications ## Deploys tools and applications to cluster

.PHONY: destroy-environment
destroy-environment: undeploy-applications undeploy-tools ## Undeploys tools and applications to cluster

.PHONY: start-scenario
start-scenario: create-environment deploy-recorders inject-scenario-faults ## Starts an scenario by deploying a stack, applications, faults, and recorders

.PHONY: stop-scenario
stop-scenario: undeploy-recorders remove-fault-resources destroy-environment ## Stops an scenario by undeploying a stack, applications, faults, and recorders

.PHONY: enable-agent-access
enable-agent-access: ## Adds access controls for llm agent
ifdef SCENARIO_NUMBER
	$(UV) run ansible-playbook -i inventory project/manage_agent_access.yaml --tags "grant_access" \
		--extra-vars "scenario_specs_directory=$(abspath ../../../library/specs/scenarios/$(SCENARIO_NUMBER))"
else
	@echo "Missing SCENARIO_NUMBER argument. Please run this command with this variable."
endif

.PHONY: disable-agent-access
disable-agent-access: ## Removes access controls for llm agent
	$(UV) run ansible-playbook -i inventory project/manage_agent_access.yaml --tags "revoke_access"

.PHONY: deploy-argo
deploy-argo: ## Deploys Argo Workflows to the orchestrator cluster
	$(UV) run ansible-playbook -i inventory project/manage_argo.yaml --tags "install_tools"

.PHONY: undeploy-argo
undeploy-argo: ## Undeploys Argo Workflows from the orchestrator cluster
	$(UV) run ansible-playbook -i inventory project/manage_argo.yaml --tags "uninstall_tools"

.PHONY: launch-start-workflow
launch-start-workflow: ## Launches the start-scenario workflow on Argo
	$(UV) run ansible-playbook -i inventory project/manage_argo.yaml --tags "launch_workflows" \
		--extra-vars "argo_workflow_type=start-scenario"

.PHONY: launch-stop-workflow
launch-stop-workflow: ## Launches the stop-scenario workflow on Argo
	$(UV) run ansible-playbook -i inventory project/manage_argo.yaml --tags "launch_workflows" \
		--extra-vars "argo_workflow_type=stop-scenario"

.PHONY: launch-data-collection-workflow
launch-data-collection-workflow: ## Launches the data-collection workflow on Argo
	$(UV) run ansible-playbook -i inventory project/manage_argo.yaml --tags "launch_workflows" \
		--extra-vars "argo_workflow_type=data-collection"

.PHONY: test-molecule-agent
test-molecule-agent: ## Runs Molecule tests for the Agent role
	cd project/roles/agent && $(UV) run molecule test --all --report --command-borders

.PHONY: test-molecule-argo
test-molecule-argo: ## Runs Molecule tests for the Argo role
	cd project/roles/argo && $(UV) run molecule test --all --report --command-borders

.PHONY: test-molecule-faults
test-molecule-faults: ## Runs Molecule tests for the Faults role
	cd project/roles/faults && $(UV) run molecule test --all --report --command-borders

.PHONY: test-molecule-waiters
test-molecule-waiters: ## Runs Molecule tests for the Waiters role
	cd project/roles/waiters && $(UV) run molecule test --all --report --command-borders

.PHONY: test-network-gateway
test-network-gateway: ## Run tool gateway network tests
	cd project/roles/tools && $(UV) run molecule test --scenario-name external_endpoints --report --command-borders

.PHONY: test-scripts
test-scripts: ## Run unit tests for Python scripts
	$(UV) run python -m unittest discover -s scripts/unittests -p "test_*.py"

.PHONY: generate-agent-bundle
generate-agent-bundle: ## Generates a bundle for an LLM Agent to interface with
	ANSIBLE_STDOUT_CALLBACK=ansible.posix.json $(UV) run ansible-playbook -i inventory project/generate_agent_bundle.yaml | jq -r '.plays[].tasks[] | select(.task.name == "Print agent bundle") | .hosts.localhost.msg'

.PHONY: generate-leaderboard-bundle-status
generate-leaderboard-bundle-status: ## Generates a bundle status for Leaderboard to interface with
	$(UV) run ansible-playbook -i inventory project/generate_leaderboard_bundle_status.yaml

.PHONY: generate-leaderboard-bundle
generate-leaderboard-bundle: ## Generates a bundle of scenarios for the Leaderboard to interface
	$(UV) run ansible-playbook -i inventory project/generate_leaderboard_bundle.yaml
