GO = $(shell which go)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: create_cluster
create_cluster: ## Creates a Kind cluster
	mkdir -p experiment-data
	sudo chown -R 1000:1000 experiment-data
	sudo chmod -R 755 experiment-data
	@# Checking CPU count and use appropriate config
	@CPU_COUNT=$$(nproc); \
	if [ $$CPU_COUNT -ge 24 ]; then \
		echo "CPU count is $$CPU_COUNT (>= 24), creating cluster with 3 nodes (1 control-plane + 2 workers)"; \
		$(GO) tool kind create cluster --config kind-config-multinode.yaml; \
	else \
		echo "CPU count is $$CPU_COUNT (< 24), creating cluster with 1 node (control-plane only)"; \
		$(GO) tool kind create cluster --config kind-config.yaml; \
	fi

.PHONY: delete_cluster
delete_cluster: ## Deletes a Kind cluster
	$(GO) tool kind delete cluster --name kind-cluster

.PHONY: start_provider
start_provider: ## Starts the Cloud Provider service for Kind
	sudo $(GO) tool cloud-provider-kind -enable-lb-port-mapping
