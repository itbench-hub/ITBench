MINIKUBE := $(shell command -v minikube)
UV := $(shell command -v uv)

# Expose component metrics endpoints so Prometheus can scrape kube-proxy, controller-manager, and scheduler
MINIKUBE_KUBEADM_CONFIG_FLAGS := --extra-config=kube-proxy.metrics-bind-address="0.0.0.0:10249" \
	--extra-config=controller-manager.bind-address="0.0.0.0" \
	--extra-config=controller-manager.authorization-always-allow-paths="/metrics" \
	--extra-config=scheduler.bind-address="0.0.0.0" \
	--extra-config=scheduler.authorization-always-allow-paths="/metrics"

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: lint
lint: ## Lints files
	$(UV) run ansible-lint

.PHONY: group-vars
group-vars: ## Generates the group variables
	mkdir -p inventory/group_vars/all
	echo "ansible_python_interpreter: $$($(UV) python find)" > inventory/group_vars/all/ansible.yaml

.PHONY: check-resources
check-resources:
	$(UV) run ansible-playbook -i inventory playbooks/check_machine_resources.yaml \
		--extra-vars "target=$(CLUSTER_TARGET)"

.PHONY: create-cluster
create-cluster:
	$(MINIKUBE) start -p $(CLUSTER_PROFILE) --nodes $(CLUSTER_NODES) $(MINIKUBE_KUBEADM_CONFIG_FLAGS)

.PHONY: destroy-cluster
destroy-cluster:
	-sudo pkill -f "minikube.*$(CLUSTER_PROFILE).*tunnel"
	-sudo $(MINIKUBE) tunnel --cleanup
	$(MINIKUBE) delete -p $(CLUSTER_PROFILE)

.PHONY: start-tunnel
start-tunnel:
	$(MINIKUBE) -p $(CLUSTER_PROFILE) tunnel

.PHONY: create-simple-cluster
create-simple-cluster: CLUSTER_PROFILE=minikube-dev
create-simple-cluster: CLUSTER_NODES=2
create-simple-cluster: CLUSTER_TARGET=single-cluster
create-simple-cluster: group-vars ## Creates Minikube cluster for local development
	$(MAKE) check-resources CLUSTER_TARGET=$(CLUSTER_TARGET)
	$(MAKE) create-cluster CLUSTER_PROFILE=$(CLUSTER_PROFILE) CLUSTER_NODES=$(CLUSTER_NODES)

.PHONY: destroy-simple-cluster
destroy-simple-cluster: CLUSTER_PROFILE=minikube-dev
destroy-simple-cluster: ## Deletes the local development Minikube cluster
	$(MAKE) destroy-cluster CLUSTER_PROFILE=$(CLUSTER_PROFILE)

.PHONY: start-simple-tunnel
start-simple-tunnel: CLUSTER_PROFILE=minikube-dev
start-simple-tunnel: ## Opens Minikube tunnel to allow external IP access to dev cluster
	$(MAKE) start-tunnel CLUSTER_PROFILE=$(CLUSTER_PROFILE)

.PHONY: create-awx-cluster
create-awx-cluster: CLUSTER_PROFILE=minikube-awx
create-awx-cluster: CLUSTER_NODES=3
create-awx-cluster: CLUSTER_TARGET=awx-stack
create-awx-cluster: group-vars ## Create a Minikube cluster for local development on AWX
	$(MAKE) check-resources CLUSTER_TARGET=$(CLUSTER_TARGET)
	$(MAKE) create-cluster CLUSTER_PROFILE=$(CLUSTER_PROFILE) CLUSTER_NODES=$(CLUSTER_NODES)

.PHONY: destroy-awx-cluster
destroy-awx-cluster: CLUSTER_PROFILE=minikube-awx
destroy-awx-cluster: ## Deletes the local development AWX Minikube cluster
	$(MAKE) destroy-cluster CLUSTER_PROFILE=$(CLUSTER_PROFILE)

.PHONY: start-awx-tunnel
start-awx-tunnel: CLUSTER_PROFILE=minikube-awx
start-awx-tunnel: ## Opens Minikube tunnel to allow external IP access to AWX cluster
	$(MAKE) start-tunnel CLUSTER_PROFILE=$(CLUSTER_PROFILE)

.PHONY: test-molecule
test-molecule: ## Run Molecule tests
	$(UV) run molecule test --all --report --command-borders
