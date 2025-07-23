GO = $(shell which go)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: create_cluster
create_cluster:## Creates a Kind cluster
	$(GO) tool kind create cluster --config kind-config.yaml

.PHONY: delete_cluster
delete_cluster: ## Deletes a Kind cluster
	$(GO) tool kind delete cluster --name kind-cluster

.PHONY: start_provider
start_provider: ## Starts the Cloud Provider service for Kind
	sudo $(GO) tool cloud-provider-kind -enable-lb-port-mapping
