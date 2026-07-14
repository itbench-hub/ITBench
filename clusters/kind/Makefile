GO := $(shell command -v go)
UV := $(shell command -v uv)

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
	$(GO) tool kind create cluster --config configs/$(CLUSTER_CONFIG_FILE)

.PHONY: destroy-cluster
destroy-cluster:
	$(GO) tool kind delete cluster --name $(CLUSTER_NAME)

.PHONY: create-simple-cluster
create-simple-cluster: CLUSTER_CONFIG_FILE=simple.yaml
create-simple-cluster: CLUSTER_TARGET=single-cluster
create-simple-cluster: group-vars ## Creates a Kind cluster for local development
	$(MAKE) check-resources CLUSTER_TARGET=$(CLUSTER_TARGET)
	$(MAKE) create-cluster CLUSTER_CONFIG_FILE=$(CLUSTER_CONFIG_FILE)

.PHONY: destroy-simple-cluster
destroy-simple-cluster: CLUSTER_NAME=kind-dev
destroy-simple-cluster: ## Deletes the local development Kind cluster
	$(MAKE) destroy-cluster CLUSTER_NAME=$(CLUSTER_NAME)

.PHONY: create-awx-cluster
create-awx-cluster: CLUSTER_CONFIG_FILE=awx.yaml
create-awx-cluster: CLUSTER_TARGET=awx-stack
create-awx-cluster: group-vars ## Create a Kind cluster for local development on AWX
	$(MAKE) check-resources CLUSTER_TARGET=$(CLUSTER_TARGET)
	$(MAKE) create-cluster CLUSTER_CONFIG_FILE=$(CLUSTER_CONFIG_FILE)

.PHONY: destroy-awx-cluster
destroy-awx-cluster: CLUSTER_NAME=kind-awx
destroy-awx-cluster: ## Deletes the local development AWX Kind cluster
	$(MAKE) destroy-cluster CLUSTER_NAME=$(CLUSTER_NAME)

.PHONY: run-service-provider
run-service-provider: ## Runs Cloud Provider Kind for Load Balancer services
	sudo $(GO) tool cloud-provider-kind --gateway-channel disabled

.PHONY: test-molecule
test-molecule: ## Run Molecule tests
	$(UV) run molecule test --all --report --command-borders
