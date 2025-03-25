# Makefile to run Ansible playbooks

EXECUTE_CHECKS_IN_BACKGROUND ?= false
USE_JAEGER_QUERY_ENDPOINT ?= true

INCIDENT_NUMBER ?= 1
NUMBER_OF_RUNS = 1
# TODO: Re-think the end to end experience

FINOPS_SCENARIOS := 37
HOTEL_RESERVATION_SCENARIOS := 102

IS_DEBUG_SCENARIO ?= true
IS_FINOPS_SCENARIO := $(shell echo "$(FINOPS_SCENARIOS)" | grep -w "$(INCIDENT_NUMBER)" > /dev/null && echo "true" || echo "false")
IS_HOTEL_RESERVATION_SCENARIO := $(shell echo "$(HOTEL_RESERVATION_SCENARIOS)" | grep -w "$(INCIDENT_NUMBER)" > /dev/null && echo "true" || echo "false")

SAMPLE_APPLICATION := otel_astronomy_shop
ifeq ($(IS_HOTEL_RESERVATION_SCENARIO),true)
SAMPLE_APPLICATION := dsb_hotel_reservation
else
endif

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: deploy_observability_stack
deploy_observability_stack: ## Deploys the observability tools to cluster
ifeq ($(USE_JAEGER_QUERY_ENDPOINT),false)
	ansible-playbook -v base.yaml --tags "install_tools" \
		--extra-vars "domain=sre" \
		--extra-vars "enable_jaeger_query_endpoint=false"
else
	ansible-playbook -v base.yaml --tags "install_tools" \
		--extra-vars "domain=sre" \
		--extra-vars "enable_jaeger_query_endpoint=true"
endif

.PHONY: undeploy_observability_stack
undeploy_observability_stack: ## Undeploys observability tools to cluster
	ansible-playbook -v base.yaml --tags "uninstall_tools" \
		--extra-vars "domain=sre"

.PHONY: deploy_finops_stack
deploy_finops_stack: ## Deploys the finops tools to cluster
	ansible-playbook -v base.yaml --tags "install_tools" \
		--extra-vars "domain=finops"

.PHONY: undeploy_finops_stack
undeploy_finops_stack: ## Undeploys finops tools to cluster
	ansible-playbook -v base.yaml --tags "uninstall_tools" \
		--extra-vars "domain=finops"

.PHONY: deploy_astronomy_shop
deploy_astronomy_shop: ## Deploys the Astronomy Shop application
	ansible-playbook -v base.yaml --tags "install_sample_applications" \
		--extra-vars "sample_application=otel_astronomy_shop"

.PHONY: undeploy_astronomy_shop
undeploy_astronomy_shop: ## Undeploys the Astronomy Shop application
	ansible-playbook -v base.yaml --tags "uninstall_sample_applications" \
		--extra-vars "sample_application=otel_astronomy_shop"

.PHONY: deploy_hotel_reservation
deploy_hotel_reservation: ## Deploys the Hotel Reservation application
	ansible-playbook -v base.yaml --tags "install_sample_applications" \
		--extra-vars "sample_application=dsb_hotel_reservation"

.PHONY: undeploy_hotel_reservation
undeploy_hotel_reservation: ## Undeploys the Hotel Reservation application
	ansible-playbook -v base.yaml --tags "uninstall_sample_applications" \
		--extra-vars "sample_application=dsb_hotel_reservation"

.PHONY: deploy_elasticsearch
deploy_elasticsearch: ## Deploys the Elasticsearch cluster
	ansible-playbook -v base.yaml --tags "install_sample_applications" \
		--extra-vars "sample_application=elasticsearch"

.PHONY: undeploy_elasticsearch
undeploy_elasticsearch: ## Undeploys the Elasticsearch cluster
	ansible-playbook -v base.yaml --tags "uninstall_sample_applications" \
		--extra-vars "sample_application=elasticsearch"

.PHONY: install_chaos_mesh
install_chaos_mesh: ## Installs a Chaos mesh to the cluster
	ansible-playbook -v base.yaml --tags "chaos_mesh_installation" \
		--extra-vars "is_install_chaos_mesh=true"

.PHONY: inject_incident_fault
inject_incident_fault: ## Injects the fault used in a specific incident
ifeq ($(IS_DEBUG_SCENARIO),true)
	ansible-playbook -v base.yaml --tags "incident_$(INCIDENT_NUMBER)" \
		--extra-vars "debug=true" \
		--extra-vars "is_fault_injection=true" \
		--extra-vars "incident_number=$(INCIDENT_NUMBER)" \
		--extra-vars "sample_application=$(SAMPLE_APPLICATION)"
else
	ansible-playbook -v base.yaml --tags "incident_$(INCIDENT_NUMBER)" \
		--extra-vars "is_fault_injection=true" \
		--extra-vars "incident_number=$(INCIDENT_NUMBER)" \
		--extra-vars "sample_application=$(SAMPLE_APPLICATION)"
endif
	ansible-playbook -v base.yaml --tags "post_fault_injection"

.PHONY: remove_incident_fault
remove_incident_fault: ## Removes the fault used in a specific incident
	ansible-playbook -v base.yaml --tags "pre_fault_removal"
ifeq ($(IS_DEBUG_SCENARIO),true)
	ansible-playbook -v base.yaml --tags "incident_$(INCIDENT_NUMBER)" \
		--extra-vars "debug=true" \
		--extra-vars "is_fault_removal=true" \
		--extra-vars "incident_number=$(INCIDENT_NUMBER)" \
		--extra-vars "sample_application=$(SAMPLE_APPLICATION)"
else
	ansible-playbook -v base.yaml --tags "incident_$(INCIDENT_NUMBER)" \
		--extra-vars "is_fault_removal=true" \
		--extra-vars "incident_number=$(INCIDENT_NUMBER)" \
		--extra-vars "sample_application=$(SAMPLE_APPLICATION)"
endif

.PHONY: deploy_scenario_application
ifeq ($(IS_HOTEL_RESERVATION_SCENARIO),true)
deploy_scenario_application: deploy_hotel_reservation
else
deploy_scenario_application: deploy_astronomy_shop
endif

.PHONY: undeploy_scenario_application
ifeq ($(IS_HOTEL_RESERVATION_SCENARIO),true)
undeploy_scenario_application: undeploy_hotel_reservation
else
undeploy_scenario_application: undeploy_astronomy_shop
endif

.PHONY: deploy_scenario_tools
ifeq ($(IS_FINOPS_SCENARIO),true)
deploy_scenario_tools: deploy_finops_stack
else
deploy_scenario_tools: deploy_observability_stack
endif

.PHONY: undeploy_scenario_tools
ifeq ($(IS_FINOPS_SCENARIO),true)
undeploy_scenario_tools: undeploy_finops_stack
else
undeploy_scenario_tools: undeploy_observability_stack
endif

.PHONY: start_incident
start_incident: deploy_scenario_tools deploy_scenario_application inject_incident_fault ## Starts an incident by deploying a stack, application, and fault for an incident

.PHONY: stop_incident
stop_incident: remove_incident_fault undeploy_scenario_application undeploy_scenario_tools ## Stops an incident by undeploying a stack, application, and fault for an incident

.PHONY: awx_setup
awx_setup:
	ansible-playbook -v base.yaml --tags "awx_setup"

.PHONY: awx_configure_init
awx_configure_init:
	ansible-playbook -v base.yaml --tags "awx_configuration" --extra-vars "state=present"

.PHONY: awx_configure_deinit
awx_configure_deinit:
	ansible-playbook -v base.yaml --tags "awx_configuration" --extra-vars "state=absent"

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

.PHONY: e2e_awx_init_stage_one
e2e_awx_init_stage_one: ## Given an incident number, run_uuid intitialize the scenario run leveraging an AWX node
	kops export kubecfg --admin --name=${AWX_CLUSTERNAME} --state=s3://${S3_BUCKET_NAME} --kubeconfig /tmp/${AWX_CLUSTERNAME}.yaml
	# Get cluster to be used configuration
	KOPS_STATE_STORE=s3://${S3_BUCKET_NAME} kops export kubecfg ${CLUSTER_ASSIGNED_NAME} --admin --kubeconfig /tmp/${CLUSTER_ASSIGNED_NAME}.yaml; \
        ansible-playbook -v base.yaml --tags "awx_scenario_setup" --extra-vars "relevant_kubeconfig_file_path=/tmp/${CLUSTER_ASSIGNED_NAME}.yaml scenario_number=${INCIDENT_NUMBER} state=present sample_application=${SAMPLE_APPLICATION} awx_kubeconfig=${AWX_KUBECONFIG} s3_bucket_name_for_results='sre-runner-with-awx' sre_bench_runner=true domain=sre"; \
	ansible-playbook -v base.yaml --tags "workflow_setup_stage_one" --extra-vars "scenario_number=${INCIDENT_NUMBER} state=present sample_application=${SAMPLE_APPLICATION} awx_kubeconfig=${AWX_KUBECONFIG} sre_bench_runner=true domain=sre s3_endpoint_url='https://s3.us-east-2.amazonaws.com'"; \
	ansible-playbook -v base.yaml --tags "workflow_launch_stage_one" --extra-vars "run_uuid=${RUN_UUID} sre_agent_name__version_number=${PARTICIPANT_AGENT_UUID} scenario_number=${INCIDENT_NUMBER} number_of_runs=${NUMBER_OF_RUNS} state=present sample_application=${SAMPLE_APPLICATION} awx_kubeconfig=${AWX_KUBECONFIG} s3_bucket_name_for_results='sre-runner-with-awx' sre_bench_runner=true domain=sre s3_endpoint_url='https://s3.us-east-2.amazonaws.com'";

.PHONY: e2e_awx_stage_three
e2e_awx_stage_three: ## Given an incident number, run_uuid end the scenario run leveraging an AWX node
	# Get cluster to be used configuration
	KOPS_STATE_STORE=s3://${S3_BUCKET_NAME} kops export kubecfg ${CLUSTER_ASSIGNED_NAME} --admin --kubeconfig /tmp/${CLUSTER_ASSIGNED_NAME}.yaml; \
	ansible-playbook -v base.yaml --tags "workflow_setup_stage_three" --extra-vars "scenario_number=${INCIDENT_NUMBER} state=present sample_application=${SAMPLE_APPLICATION} awx_kubeconfig=${AWX_KUBECONFIG} sre_bench_runner=true domain=sre s3_endpoint_url='https://s3.us-east-2.amazonaws.com'"; \
	ansible-playbook -v base.yaml --tags "workflow_launch_stage_three" --extra-vars "run_uuid=${RUN_UUID} sre_agent_name__version_number=${PARTICIPANT_AGENT_UUID} scenario_number=${INCIDENT_NUMBER} number_of_runs=${NUMBER_OF_RUNS} state=present sample_application=${SAMPLE_APPLICATION} awx_kubeconfig=${AWX_KUBECONFIG} s3_bucket_name_for_results='sre-runner-with-awx' sre_bench_runner=true domain=sre s3_endpoint_url='https://s3.us-east-2.amazonaws.com'";

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

.SILENT: bundle_info
bundle_info:
	ANSIBLE_STDOUT_CALLBACK=json ansible-playbook base.yaml --tags "get_bundle_info" --extra-vars "run_uuid=${RUN_UUID} sre_agent_name__version_number=${PARTICIPANT_AGENT_UUID} scenario_number=${INCIDENT_NUMBER} run_number=1 s3_bucket_name_for_results='sre-runner-with-awx' sre_bench_runner=true kubeconfig=/tmp/${CLUSTER_ASSIGNED_NAME}.yaml s3_endpoint_url='https://s3.us-east-2.amazonaws.com'" | jq '.plays[].tasks[] | select(.task.name == "bundle_info : Return grafana url").hosts.localhost.msg'
