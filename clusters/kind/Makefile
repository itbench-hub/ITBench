GO := $(shell command -v go)
UV := $(shell command -v uv)

ENVIRONMENT_CLUSTER_NAME 	?= itbench-environment
ORCHESTRATOR_CLUSTER_NAME	?= itbench-orchestrator

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: check-resources
check-resources:
	$(UV) run python $(abspath ../../scripts/check_localhost_resources.py) --target $(CLUSTER_TARGET)

kubeconfigs:
	mkdir -p $@

.PHONY: create-cluster
create-cluster: kubeconfigs
	$(GO) tool kind create cluster --name $(CLUSTER_NAME) \
		--config $(abspath configs/$(CLUSTER_CONFIG_FILE))
	$(GO) tool kind export kubeconfig --name $(CLUSTER_NAME) \
		--kubeconfig $(abspath kubeconfigs/$(CLUSTER_NAME))

.PHONY: destroy-cluster
destroy-cluster:
	$(GO) tool kind delete cluster --name $(CLUSTER_NAME)

.PHONY: create-environment-cluster
create-environment-cluster: ## Creates a Kind cluster for local development
	$(MAKE) check-resources CLUSTER_TARGET=environment-cluster
	$(MAKE) create-cluster CLUSTER_CONFIG_FILE=environment.yaml CLUSTER_NAME=$(ENVIRONMENT_CLUSTER_NAME)
	KUBECONFIG=$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_NAME)) \
		$(UV) run python $(abspath ../../scripts/configure_environment_cluster.py)
	@printf 'K8S_AUTH_KUBECONFIG=%s\n' "$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_NAME))" > $(abspath ../../scenarios/sre/.env)
	@echo "Run the following command to access the cluster ($(ENVIRONMENT_CLUSTER_NAME)) using kubectl:"
	@echo "export KUBECONFIG=$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_NAME))"

.PHONY: destroy-environment-cluster
destroy-environment-cluster: ## Deletes the local development Kind cluster
	$(MAKE) destroy-cluster CLUSTER_NAME=$(ENVIRONMENT_CLUSTER_NAME)

.PHONY: create-argo-stack
create-argo-stack: ## Creates a two-cluster Kind stack for Argo Workflows orchestration
	$(MAKE) check-resources CLUSTER_TARGET=argo-stack
	$(MAKE) create-cluster CLUSTER_CONFIG_FILE=argo.yaml CLUSTER_NAME=$(ORCHESTRATOR_CLUSTER_NAME)
	$(MAKE) create-cluster CLUSTER_CONFIG_FILE=environment.yaml CLUSTER_NAME=$(ENVIRONMENT_CLUSTER_NAME)
	KUBECONFIG=$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_NAME)) \
		$(UV) run python $(abspath ../../scripts/configure_environment_cluster.py)
	@printf 'K8S_AUTH_KUBECONFIG=%s\n' "$(abspath kubeconfigs/$(ORCHESTRATOR_CLUSTER_NAME))" > $(abspath ../../scenarios/sre/.env)
	@printf '---\nstack:\n  environments:\n    - kubeconfig: %s\n' \
		"$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_NAME))" \
		> $(abspath ../../scenarios/sre/inventory/group_vars/orchestrator/stack.yaml)
	@echo "Run the following commands to access the orchestrator cluster ($(ORCHESTRATOR_CLUSTER_NAME)) using kubectl:"
	@echo "export KUBECONFIG=$(abspath kubeconfigs/$(ORCHESTRATOR_CLUSTER_NAME))"

.PHONY: destroy-argo-stack
destroy-argo-stack: ## Deletes the local development Argo Kind cluster
	$(MAKE) destroy-cluster CLUSTER_NAME=$(ORCHESTRATOR_CLUSTER_NAME)
	$(MAKE) destroy-cluster CLUSTER_NAME=$(ENVIRONMENT_CLUSTER_NAME)

.PHONY: run-service-provider
run-service-provider: ## Runs Cloud Provider Kind for Load Balancer services
	$(GO) tool cloud-provider-kind --gateway-channel disabled
