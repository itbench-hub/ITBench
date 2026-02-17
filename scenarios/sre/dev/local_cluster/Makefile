GO = $(shell which go)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: create-simple-cluster
create-simple-cluster: ## Creates a Kind cluster for local development
ifeq ($(shell uname -s), "Darwin")
	@if [ $(shell sysctl -n hw.logicalcpu) -lt 8 ]; then \
		echo "This machine does not have the recommended amount of CPU (8+)."; \
		echo "You may experience degredated or inconsistent performance on this machine,"; \
	fi
else
	@if [ $(shell nproc) -lt 8 ]; then \
		echo "This machine does not have the recommended amount of CPU (8+)."; \
		echo "You may experience degredated or inconsistent performance on this machine,"; \
	fi
endif
	$(GO) tool kind create cluster --config kind/configs/simple.yaml

.PHONY: create-awx-cluster
create-awx-cluster: ## Create a Kind cluster for local development on AWX
ifeq ($(shell uname -s), "Darwin")
	@if [ $(shell sysctl -n hw.logicalcpu) -lt 24 ]; then \
		echo "This machine does not have the recommended amount of CPU (24+)."; \
		echo "You may experience degredated or inconsistent performance on this machine."; \
	fi
else
	@if [ $(shell nproc) -lt 24 ]; then \
		echo "This machine does not have the recommended amount of CPU (24+)."; \
		echo "You may experience degredated or inconsistent performance on this machine."; \
	fi
endif
	$(GO) tool kind create cluster --config kind/configs/awx.yaml

.PHONY: destroy-simple-cluster
destroy-simple-cluster: ## Deletes the local development Kind cluster
	$(GO) tool kind delete cluster --name kind-dev

.PHONY: destroy-awx-cluster
destroy-awx-cluster: ## Deletes the local development AWX Kind cluster
	$(GO) tool kind delete cluster --name kind-awx

.PHONY: run-service-provider
run-service-provider: ## Runs Cloud Provider Kind for Load Balancer services
	$(GO) tool cloud-provider-kind --gateway-channel disabled
