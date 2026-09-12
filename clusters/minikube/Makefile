MINIKUBE := $(shell command -v minikube)
UV := $(shell command -v uv)

ENVIRONMENT_CLUSTER_PROFILE 	?= itbench-environment
ORCHESTRATOR_CLUSTER_PROFILE	?= itbench-orchestrator

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
	KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_PROFILE)) \
		$(MINIKUBE) start -p $(CLUSTER_PROFILE) \
		--nodes 2 \
		--extra-config=kube-proxy.metrics-bind-address="0.0.0.0:10249" \
		--extra-config=controller-manager.bind-address="0.0.0.0" \
		--extra-config=controller-manager.authorization-always-allow-paths="/metrics" \
		--extra-config=scheduler.bind-address="0.0.0.0" \
		--extra-config=scheduler.authorization-always-allow-paths="/metrics"

.PHONY: destroy-cluster
destroy-cluster:
	-sudo pkill -f "minikube.*$(CLUSTER_PROFILE).*tunnel"
	-sudo KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_PROFILE)) \
		$(MINIKUBE) tunnel -p $(CLUSTER_PROFILE) --cleanup
	KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_PROFILE)) \
		$(MINIKUBE) delete -p $(CLUSTER_PROFILE)

.PHONY: start-tunnel
start-tunnel:
	KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_PROFILE)) \
		$(MINIKUBE) -p $(CLUSTER_PROFILE) tunnel

.PHONY: create-environment-cluster
create-environment-cluster: ## Creates Minikube cluster for local development
	$(MAKE) check-resources CLUSTER_TARGET=environment-cluster
	$(MAKE) create-cluster CLUSTER_PROFILE=$(ENVIRONMENT_CLUSTER_PROFILE)
	KUBECONFIG=$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_PROFILE)) \
		$(UV) run python $(abspath ../../scripts/configure_environment_cluster.py)
	@printf 'K8S_AUTH_KUBECONFIG=%s\n' "$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_PROFILE))" > $(abspath ../../scenarios/sre/.env)
	@echo "Run the following commands to access the cluster ($(ENVIRONMENT_CLUSTER_PROFILE)) using kubectl:"
	@echo "export KUBECONFIG=$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_PROFILE))"

.PHONY: destroy-environment-cluster
destroy-environment-cluster: ## Deletes the local development Minikube cluster
	$(MAKE) destroy-cluster CLUSTER_PROFILE=$(ENVIRONMENT_CLUSTER_PROFILE)

.PHONY: start-environment-tunnel
start-environment-tunnel: ## Opens Minikube tunnel to allow external IP access to dev cluster
	$(MAKE) start-tunnel CLUSTER_PROFILE=$(ENVIRONMENT_CLUSTER_PROFILE)

.PHONY: create-argo-stack
create-argo-stack: ## Creates a two-cluster Minikube stack for Argo Workflows orchestration
	$(MAKE) check-resources CLUSTER_TARGET=argo-stack
	$(MAKE) create-cluster CLUSTER_PROFILE=$(ORCHESTRATOR_CLUSTER_PROFILE)
	$(MAKE) create-cluster CLUSTER_PROFILE=$(ENVIRONMENT_CLUSTER_PROFILE)
	KUBECONFIG=$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_PROFILE)) \
		$(UV) run python $(abspath ../../scripts/configure_environment_cluster.py)
	@printf 'K8S_AUTH_KUBECONFIG=%s\n' "$(abspath kubeconfigs/$(ORCHESTRATOR_CLUSTER_PROFILE))" > $(abspath ../../scenarios/sre/.env)
	@printf '---\nstack:\n  environments:\n    - kubeconfig: %s\n' \
		"$(abspath kubeconfigs/$(ENVIRONMENT_CLUSTER_PROFILE))" \
		> $(abspath ../../scenarios/sre/inventory/group_vars/orchestrator/stack.yaml)
	@echo "Run the following commands to access the orchestrator cluster ($(ORCHESTRATOR_CLUSTER_PROFILE)) using kubectl:"
	@echo "export KUBECONFIG=$(abspath kubeconfigs/$(ORCHESTRATOR_CLUSTER_PROFILE))"

.PHONY: destroy-argo-stack
destroy-argo-stack: ## Deletes the Argo Minikube stack
	$(MAKE) destroy-cluster CLUSTER_PROFILE=$(ORCHESTRATOR_CLUSTER_PROFILE)
	$(MAKE) destroy-cluster CLUSTER_PROFILE=$(ENVIRONMENT_CLUSTER_PROFILE)

.PHONY: start-argo-tunnel
start-argo-tunnel: ## Opens Minikube tunnel for the Argo orchestrator cluster
	$(MAKE) start-tunnel CLUSTER_PROFILE=$(ORCHESTRATOR_CLUSTER_PROFILE)
