# Makefile to run Ansible playbooks

NUMBER_OF_RUNS = 1


.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: group_vars
group_vars: ## Generates the group variables
	echo "ansible_python_interpreter: $(shell which python)" > group_vars/all/ansible.yaml
	cp group_vars/all/storage.yaml.example group_vars/all/storage.yaml
	cp group_vars/environment/applications.yaml.example group_vars/environment/applications.yaml
	cp group_vars/environment/cluster.yaml.example group_vars/environment/cluster.yaml
	cp group_vars/environment/tools.yaml.example group_vars/environment/tools.yaml

.PHONY: docs
docs: ## Generates the documentation for the incidents
	ansible-playbook -i inventory.yaml playbooks/manage_documentation.yaml --tags "generate_docs"

.PHONY: validate_docs
validate_docs: ## Validates the documents (ie: specs) used to run an incident
	ansible-playbook -i inventory.yaml playbooks/manage_documentation.yaml --tags "validate_docs"

.PHONY: deploy_tools
deploy_tools: ## Deploys the observability and fault tools to cluster
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "install_tools" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "install_tools"
endif

.PHONY: reinit_tools
reinit_tools: ## Re-initialize observability and fault tools to cluster
	ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "reinit_tools"

.PHONY: undeploy_tools
undeploy_tools: ## Undeploys the observability and fault tools to cluster
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "uninstall_tools" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_tools.yaml --tags "uninstall_tools"
endif

.PHONY: deploy_applications
deploy_applications: ## Deploys the applications to cluster
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "install_applications" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "install_applications"
endif

.PHONY: undeploy_applications
undeploy_applications: ## Undeploys the applications to cluster
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "uninstall_applications" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_applications.yaml --tags "uninstall_applications"
endif

.PHONY: deploy_recorders
deploy_recorders: ## Deploys the data recorders to cluster
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "install_recorders" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "install_recorders"
endif

.PHONY: undeploy_recorders
undeploy_recorders: ## Undeploys the data recorders to cluster
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "uninstall_recorders" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_recorders.yaml --tags "uninstall_recorders"
endif

.PHONY: inject_incident_fault
inject_incident_fault: ## Injects the fault used in a specific incident
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_incidents.yaml --tags "inject_faults" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	@echo "Missing INCIDENT_NUMBER argument. Please run this command with this variable."
endif

.PHONY: remove_incident_fault
remove_incident_fault: ## Removes the fault used in a specific incident
ifdef INCIDENT_NUMBER
	ansible-playbook -i inventory.yaml playbooks/manage_incidents.yaml --tags "remove_faults" \
		--extra-vars "incident_id=$(INCIDENT_NUMBER)"
else
	@echo "Missing INCIDENT_NUMBER argument. Please run this command with this variable."
endif

.PHONY: create_environment
create_environment: deploy_tools deploy_applications ## Deploys tools and applications to cluster

.PHONY: destroy_environment
destroy_environment: undeploy_applications undeploy_tools ## Undeploys tools and applications to cluster

.PHONY: start_incident
start_incident: create_environment deploy_recorders inject_incident_fault ## Starts an incident by deploying a stack, applications, faults, and recorders for an incident

.PHONY: stop_incident
stop_incident: undeploy_recorders remove_incident_fault destroy_environment ## Stops an incident by undeploying a stack, applications, faults, and recorders for an incident

.PHONY: enable_agent_access
enable_agent_access: ## Adds access controls for llm agent
	ansible-playbook -i inventory.yaml playbooks/manage_agent_access.yaml --tags "grant_access"

.PHONY: disable_agent_access
disable_agent_access: ## Removes access controls for llm agent
	ansible-playbook -i inventory.yaml playbooks/manage_agent_access.yaml --tags "revoke_access"

.PHONY: generate_agent_bundle
generate_agent_bundle: ## Generates a bundle for an LLM Agent to interface with
	ANSIBLE_STDOUT_CALLBACK=ansible.posix.json ansible-playbook -i inventory.yaml playbooks/generate_agent_bundle.yaml | jq -r '.plays[].tasks[] | select(.task.name == "Print agent bundle") | .hosts.localhost.msg'

.PHONY: generate_leaderboard_bundle_status
generate_leaderboard_bundle_status: ## Generates a bundle status for Leaderboard to interface with
	ansible-playbook -i inventory.yaml playbooks/generate_leaderboard_bundle_status.yaml

.PHONY: generate_leaderboard_bundle
generate_leaderboard_bundle: ## Generates a bundle of scenarios for the Leaderboard to interface
	ansible-playbook -i inventory.yaml playbooks/generate_leaderboard_bundle.yaml

PHONY: fetch_alerts
fetch_alerts: ## Checks the Prometheus for firing alerts
	ansible-runner run ./ -p check_for_specific_alerts_in_firing_state.yaml

.PHONY: deploy_observability_stack
deploy_observability_stack: ## DEPRECATED: Deploys the observability tools to cluster
	@echo "WARNING: 'make deploy_observability_stack' is deprecated. Please use 'make deploy_environment_tools' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make deploy_tools'..."
	@echo ""
	$(MAKE) deploy_tools $(if $(INCIDENT_NUMBER),INCIDENT_NUMBER=$(INCIDENT_NUMBER))

.PHONY: undeploy_observability_stack
undeploy_observability_stack: ## DEPRECATED: Undeploys observability tools to cluster
	@echo "WARNING: 'make undeploy_observability_stack' is deprecated. Please use 'make deploy_environment_tools' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make undeploy_environment_tools'..."
	@echo ""
	$(MAKE) undeploy_tools $(if $(INCIDENT_NUMBER),INCIDENT_NUMBER=$(INCIDENT_NUMBER))

.PHONY: deploy_finops_stack
deploy_finops_stack: ## DEPRECATED: Deploys the finops tools to cluster
	@echo "WARNING: 'make deploy_finops_stack' is deprecated. Please use 'make deploy_environment_tools' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make deploy_environment_tools'..."
	@echo ""
	$(MAKE) deploy_tools $(if $(INCIDENT_NUMBER),INCIDENT_NUMBER=$(INCIDENT_NUMBER))

.PHONY: undeploy_finops_stack
undeploy_finops_stack: ## DEPRECATED: Undeploys finops tools to cluster
	@echo "WARNING: 'make undeploy_finops_stack' is deprecated. Please use 'make undeploy_environment_tools' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make undeploy_environment_tools'..."
	@echo ""
	$(MAKE) undeploy_tools $(if $(INCIDENT_NUMBER),INCIDENT_NUMBER=$(INCIDENT_NUMBER))

.PHONY: deploy_astronomy_shop
deploy_astronomy_shop: ## DEPRECATED: Deploys the Astronomy Shop application
	@echo "WARNING: 'make deploy_astronomy_shop' is deprecated. Please use 'make deploy_applications' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make deploy_applications'..."
	@echo ""
	$(MAKE) deploy_applications $(if $(INCIDENT_NUMBER),INCIDENT_NUMBER=$(INCIDENT_NUMBER))

.PHONY: undeploy_astronomy_shop
undeploy_astronomy_shop: ## DEPRECATED: Undeploys the Astronomy Shop application
	@echo "WARNING: 'make undeploy_astronomy_shop' is deprecated. Please use 'make undeploy_applications' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make undeploy_applications'..."
	@echo ""
	$(MAKE) undeploy_applications $(if $(INCIDENT_NUMBER),INCIDENT_NUMBER=$(INCIDENT_NUMBER))

.PHONY: deploy_hotel_reservation
deploy_hotel_reservation: ## DEPRECATED: Deploys the Hotel Reservation application
	@echo "WARNING: Hotel Reservation has been removed. Please use a pre-release version of ITBench to run scenarios with this application."
	@echo "This command will be removed in a future version."

.PHONY: undeploy_hotel_reservation
undeploy_hotel_reservation: ## DEPRECATED: Undeploys the Hotel Reservation application
	@echo "WARNING: Hotel Reservation has been removed. Please use a pre-release version of ITBench to run scenarios with this application."
	@echo "This command will be removed in a future version."

.PHONY: deploy_elasticsearch
deploy_elasticsearch: ## DEPRECATED: Deploys the Elasticsearch cluster
	@echo "WARNING: Elasticsearch has been removed. Please use a pre-release version of ITBench to run scenarios with this application."
	@echo "This command will be removed in a future version."

.PHONY: undeploy_elasticsearch
undeploy_elasticsearch: ## DEPRECATED: Undeploys the Elasticsearch cluster
	@echo "WARNING: Elasticsearch has been removed. Please use a pre-release version of ITBench to run scenarios with this application."
	@echo "This command will be removed in a future version."

.SILENT: bundle_info
bundle_info:
	@echo "WARNING: 'make bundle_info is deprecated. Please use 'make generate_agent_bundle' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make generate_agent_bundle'..."
	@echo ""
	$(MAKE) generate_agent_bundle

.SILENT: bundle_status
bundle_status:
	@echo "WARNING: 'make bundle_status is deprecated. Please use 'make generate_leaderboard_bundle_status' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make generate_leaderboard_bundle_status'..."
	@echo ""
	$(MAKE) generate_leaderboard_bundle_status

.PHONY: check_alerts
check_alerts:
	@echo "WARNING: 'make check_alerts' is deprecated. Please use 'make deploy_recorders' instead."
	@echo "This command will be removed in a future version."

.PHONY: documentation
documentation: ## DEPRECATED: Generates documentation for all incidents
	@echo "WARNING: 'make documentation is deprecated. Please use 'make docs' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make docs'..."
	@echo ""
	$(MAKE) docs

.PHONY: injection_docs
injection_docs: ## DEPRECATED: Generates documentation for all fault injection
	@echo "WARNING: 'make injection_docs' is deprecated."
	@echo "This command will be removed in a future version."
