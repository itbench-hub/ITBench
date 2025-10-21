GO = $(shell which go)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: create_data_directory
create_data_directory: ## Creates the data directory where information is stored
	mkdir -p experiment-data
	sudo chown -R 1000:1000 experiment-data
	sudo chmod -R 755 experiment-data

.PHONY: delete_data_directory
delete_data_directory: ## Deletes the data directory where information is stored
	rm -rf experiment-data

.PHONY: create_multi_node_cluster
create_multi_node_cluster: create_data_directory ## Creates a Kind cluster with a control-plane node and two worker nodes
	@if [ $(shell sysctl -n hw.logicalcpu) -ge 24]; then \
		$(GO) tool kind create cluster --config kind-config-multinode.yaml; \
	else \
		echo "This machine does not have enough CPUs (24+) to create a multinode cluster"; \
		echo "Please create a single node cluster with make create_single_node_cluster"; \
	fi

.PHONY: create_single_node_cluster
create_single_node_cluster: create_data_directory ## Creates a Kind cluster with a single control-plane node
	$(GO) tool kind create cluster --config kind-config-single-node.yaml

.PHONY: destroy_cluster
destroy_cluster: ## Deletes a Kind cluster
	$(GO) tool kind delete cluster --name kind-cluster

.PHONY: create_cluster
create_cluster: ## DEPRECATED: Creates a Kind cluster
	@echo "WARNING: 'make create_single_node_cluster is deprecated. Please use 'make create_single_node_cluster' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make create_single_node_cluster'..."
	@echo ""
	$(MAKE) create_single_node_cluster

.PHONY: delete_cluster
delete_cluster: ## DEPRECATED: Deletes a Kind cluster
	@echo "WARNING: 'make delete_cluster is deprecated. Please use 'make destory_cluster' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make destory_cluster'..."
	@echo ""
	$(MAKE) destory_cluster
