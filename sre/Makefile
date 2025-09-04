# Makefile to run Ansible playbooks

EXECUTE_CHECKS_IN_BACKGROUND ?= false

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
	cp group_vars/runner/agent.yaml.example group_vars/runner/agent.yaml
	cp group_vars/runner/credentials.yaml.example group_vars/runner/credentials.yaml
	cp group_vars/runner/experiments.yaml.example group_vars/runner/experiments.yaml
	cp group_vars/runner/github.yaml.example group_vars/runner/github.yaml
	cp group_vars/runner/stack.yaml.example group_vars/runner/stack.yaml

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
start_incident: create_environment inject_incident_fault ## Starts an incident by deploying a stack, application, and fault for an incident

.PHONY: stop_incident
stop_incident: remove_incident_fault destroy_environment ## Stops an incident by undeploying a stack, application, and fault for an incident

.PHONY: deploy_awx_stack
deploy_awx_stack: ## Deploys AWX to a cluster
	ansible-playbook -i inventory.yaml playbooks/manage_awx.yaml --tags "install_tools"

.PHONY: undeploy_awx_stack
undeploy_awx_stack: ## Undeploys AWX to a cluster
	ansible-playbook -i inventory.yaml playbooks/manage_awx.yaml --tags "uninstall_tools"

.PHONY: launch_start_incident_workflow
launch_start_workflow: ## Launches the AWX workflow's equivalent of make start_incident
	ansible-playbook -i inventory.yaml playbooks/manage_awx.yaml --tags "launch_start_workflow"

launch_stop_workflow: ## Launches the AWX workflow's equivalent of make stop_incident
	ansible-playbook -i inventory.yaml playbooks/manage_awx.yaml --tags "launch_stop_workflow"

.PHONY: generate_agent_bundle
generate_agent_bundle: ## Generates a bundle for an LLM Agent to interface with
	ANSIBLE_STDOUT_CALLBACK=ansible.posix.json ansible-playbook -i inventory.yaml playbooks/generate_agent_bundle.yaml | jq -r '.plays[].tasks[] | select(.task.name == "Print agent bundle") | .hosts.localhost.msg'

# TODO: See why the OBJC_DISABLE_INITIALIZE_FORK_SAFETY is needed

.PHONY: incident documentation
documentation: ## Generates documentation for all incidents
	export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES; \
	ansible-playbook base.yaml --tags "documentation"

.PHONY: validate_docs
validate_docs: ## Validates documention for an incident
	export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES; \
	ansible-playbook base.yaml --tags "single_doc_validate,incident_$(INCIDENT_NUMBER)" \
		--extra-vars "doc_incident_number=$(INCIDENT_NUMBER)"

.PHONY: Fault injection documentation
injection_docs: ## Generates documentation for all fault injection
	export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES; \
	ansible-playbook base.yaml --tags "injection_docs"

.PHONY: check_alerts
check_alerts:
ifeq ($(EXECUTE_CHECKS_IN_BACKGROUND),false)
	ansible-playbook -v base.yaml --tags "book_keeping" \
		--extra-vars "is_book_keeping=true" \
		--extra-vars "sample_application=$(SAMPLE_APPLICATION)" \
		$(BOOK_KEEPING_EXTRA_VARS)
else
	nohup ansible-playbook -v base.yaml --tags "book_keeping" \
		--extra-vars "is_book_keeping=true" \
		--extra-vars "sample_application=$(SAMPLE_APPLICATION)" \
		$(BOOK_KEEPING_EXTRA_VARS) &
endif

.SILENT: fetch_alerts
fetch_alerts:
	ansible-playbook -v base.yaml --tags "fetch_alerts" \
		--extra-vars "incident_number=$(INCIDENT_NUMBER)" \
		--extra-vars "sample_application=$(SAMPLE_APPLICATION)" \
		> /tmp/fetch.out 2>&1 &

.PHONY: evaluation
.SILENT: evaluation
evaluation:
	KOPS_STATE_STORE=s3://${S3_BUCKET_NAME} kops export kubecfg ${CLUSTER_ASSIGNED_NAME} --admin --kubeconfig /tmp/${CLUSTER_ASSIGNED_NAME}.yaml > /tmp/eval.out; \
	ansible-playbook -v base.yaml --tags "evaluation" --extra-vars "incident_number=$(INCIDENT_NUMBER) \
	                                                                shared_workspace=\"$(SHARED_WORKSPACE)\" \
																	s3_bucket_name_for_results='sre-runner-with-awx' \
																	sre_agent_name__version_number=${PARTICIPANT_AGENT_UUID} \
																	run_uuid=${RUN_UUID} \
																	scenario_number=$(INCIDENT_NUMBER) \
																	run_number=1  \
																	location=${location} \
																	sre_bench_runner=true \
																	kubeconfig=/tmp/${CLUSTER_ASSIGNED_NAME}.yaml \
																	domain=sre s3_endpoint_url='https://s3.us-east-2.amazonaws.com'" > /tmp/eval.out ; \
	cat evaluation/e2e_new/incident_reports/$(INCIDENT_NUMBER).json
	rm evaluation/e2e_new/incident_reports/$(INCIDENT_NUMBER).json

.SILENT: bundle_status
bundle_status:
	ansible-playbook base.yaml --tags "bundle_status" --extra-vars "run_uuid=${RUN_UUID} sre_agent_name__version_number=${PARTICIPANT_AGENT_UUID} scenario_number=${INCIDENT_NUMBER} run_number=1 bundle_status_file=roles/bundle_status/status-$$INCIDENT_NUMBER.json s3_bucket_name_for_results='sre-runner-with-awx' sre_bench_runner=true domain=sre s3_endpoint_url='https://s3.us-east-2.amazonaws.com'" > /tmp/status.out; \
	cat roles/bundle_status/status-${INCIDENT_NUMBER}.json
	rm roles/bundle_status/status-${INCIDENT_NUMBER}.json

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

.PHONY: awx_configure_init
awx_configure_init:
	@echo "WARNING: 'make awx_configure_init' is deprecated. Please use 'make deploy_awx_stack' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make deploy_awx_stack'..."
	@echo ""
	$(MAKE) deploy_awx_stack

.PHONY: awx_configure_deinit
awx_configure_deinit:
	@echo "WARNING: 'make awx_configure_deinit' is deprecated. Please use 'make undeploy_awx_stack' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make undeploy_awx_stack'..."
	@echo ""
	$(MAKE) undeploy_awx_stack

.PHONY: e2e_awx_init_stage_one
e2e_awx_init_stage_one: ## DEPRECATED: Given an incident number, run_uuid intitialize the scenario run leveraging an AWX node
	@echo "WARNING: 'make e2e_awx_init_stage_one' is deprecated. Please use 'make launch_start_workflow' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make launch_start_workflow'..."
	@echo ""
	$(MAKE) launch_start_workflow

.PHONY: e2e_awx_stage_three
e2e_awx_stage_three: ## DEPRECATED: Given an incident number, run_uuid end the scenario run leveraging an AWX node
	@echo "WARNING: 'make e2e_awx_stage_three' is deprecated. Please use 'make launch_stop_workflow' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make launch_stop_workflow'..."
	@echo ""
	$(MAKE) launch_stop_workflow

.SILENT: bundle_info
bundle_info:
	@echo "WARNING: 'make bundle_info is deprecated. Please use 'make generate_agent_bundle' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make generate_agent_bundle'..."
	@echo ""
	$(MAKE) generate_agent_bundle
