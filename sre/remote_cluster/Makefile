# Makefile to run Ansible playbooks

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: configure_localmachine
configure_localmachine: ## Configures the local machine with the necessary dependencies
	@echo "configure playbooks/variables.yaml and playbooks/secret.yaml"
	ansible-playbook playbooks/configure_localmachine.yaml --ask-become-pass

.PHONY: configure_aws_access
configure_aws_access: ## Creates and configures the AWS credentials files on the local machine
	ansible-playbook playbooks/configure_aws_user_and_storage.yaml

.PHONY: create
create: ## Creates a cluster
	ansible-playbook playbooks/create_cluster.yaml

.PHONY: batch_create
batch_create: ## Creates a batch of cluters
	ansible-playbook playbooks/batch_create_cluster.yaml

.PHONY: delete
delete: list_clusters ## Deletes a single cluster
	ansible-playbook playbooks/delete_cluster.yaml

.PHONY: batch_delete
batch_delete: ## Deletes a batch of clusters
	ansible-playbook playbooks/batch_delete_cluster.yaml

.PHONY: destroy_all_clusters
destroy_all_clusters: ## Deletes all clusters
	ansible-playbook playbooks/destroy_all_clusters.yaml

.PHONY: get_kcfg
get_kcfg: ## Retrieves the kubeconfig for a single cluster
	@echo "exports /tmp/ directory"
	ansible-playbook playbooks/get_kcfg.yaml

.PHONY: list_clusters
list_clusters: ## Lists all active clusters
	ansible-playbook playbooks/list_clusters.yaml

.PHONY: start
start: list_clusters ## Starts an inactive cluster
	@echo "edit the file to set size both controller and workers to the desired value with min = max values = desired value"
	ansible-playbook playbooks/edit_clustersize.yaml

.PHONY: stop
stop: list_clusters ## Suspends an active cluster
	@echo "edit the file to set size both controller and workers to be zero for min and max values"
	ansible-playbook playbooks/edit_clustersize.yaml

.PHONY: resize
resize: list_clusters ## Resizes an active cluster
	@echo "edit the file to set size both controller and workers to the desired value with min = max values = desired value"
	ansible-playbook playbooks/edit_clustersize.yaml 

.PHONY: install_istio_monitoring
install_istio_monitoring: list_clusters ## Installs istio/prometheus/cadvisor monitoring on the cluster
	ansible-playbook playbooks/install-istio-based-monitoring.yaml
