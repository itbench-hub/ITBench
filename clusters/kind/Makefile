GO = $(shell which go)
UV = $(shell which uv)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: lint
lint: ## Lints files
	uv run ansible-lint

.PHONY: group-vars
group-vars: ## Generates the group variables
	mkdir -p inventory/group_vars/all
	echo "ansible_python_interpreter: $(shell uv python find)" > inventory/group_vars/all/ansible.yaml

.PHONY: create-simple-cluster
create-simple-cluster: group-vars ## Creates a Kind cluster for local development
	$(UV) run ansible-playbook -i inventory playbooks/check_machine_resources.yaml \
		--extra-vars "target=single-cluster"
	$(GO) tool kind create cluster --config configs/simple.yaml

.PHONY: create-awx-cluster
create-awx-cluster: group-vars ## Create a Kind cluster for local development on AWX
	$(UV) run ansible-playbook -i inventory playbooks/check_machine_resources.yaml \
		--extra-vars "target=awx-stack"
	$(GO) tool kind create cluster --config configs/awx.yaml

.PHONY: destroy-simple-cluster
destroy-simple-cluster: ## Deletes the local development Kind cluster
	$(GO) tool kind delete cluster --name kind-dev

.PHONY: destroy-awx-cluster
destroy-awx-cluster: ## Deletes the local development AWX Kind cluster
	$(GO) tool kind delete cluster --name kind-awx

.PHONY: run-service-provider
run-service-provider: ## Runs Cloud Provider Kind for Load Balancer services
	$(GO) tool cloud-provider-kind --enable-lb-port-mapping --gateway-channel disabled
