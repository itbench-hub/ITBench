# Makefile to run Ansible playbooks

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: group_vars
group_vars: ## Generates the group variables
	mkdir group_vars/all
	echo "ansible_python_interpreter: $(shell which python)" > group_vars/all/ansible.yaml
	cp group_vars/development/awx_stack.yaml.example group_vars/development/awx_stack.yaml
	cp group_vars/development/kops_cluster.yaml.example group_vars/development/kops_cluster.yaml

.PHONY: create_kops_cluster
create_kops_cluster: ## Creates a single cluster created by kops
	ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "create_cluster"

.PHONY: list_kops_clusters
list_kops_clusters: ## Lists all active clusters created by kops
	ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "list_clusters"

.PHONY: export_kops_kubeconfig
export_kops_kubeconfig: ## Exports the kubeconfig of a single cluster created by kops
ifdef CLUSTER_NAME
	ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "export_cluster" \
		--extra-vars "kops_full_cluster_name_override=$(CLUSTER_NAME)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "export_cluster"
endif

.PHONY: destroy_kops_cluster
destroy_kops_cluster: ## Deletes a single cluster created by kops
ifdef CLUSTER_NAME
	ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "delete_cluster" \
		--extra-vars "kops_full_cluster_name_override=$(CLUSTER_NAME)"
else
	ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "delete_cluster"
endif

.PHONY: create_awx_stack
create_awx_stack: ## Creates an AWX stack created by kops
	ansible-playbook -i inventory.yaml playbooks/manage_awx_stack.yaml --tags "create_stack"

.PHONY: export_awx_kubeconfigs
export_awx_kubeconfigs: ## Exports the kubeconfigs of all clusters used in an AWX stack
	ansible-playbook -i inventory.yaml playbooks/manage_awx_stack.yaml --tags "export_stack"

.PHONY: destroy_awx_stack
destroy_awx_stack: ## Destroy an AWX stack created by kops
	ansible-playbook -i inventory.yaml playbooks/manage_awx_stack.yaml --tags "delete_stack"

.PHONY: create
create: ## DEPRECATED: Use 'make create_kops_cluster' instead. Creates a single cluster
	@echo "WARNING: 'make create' is deprecated. Please use 'make create_kops_cluster' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make create_kops_cluster'..."
	@echo ""
	$(MAKE) create_kops_cluster

.PHONY: list_clusters
list_clusters: ## DEPRECATED: Use 'make list_kops_cluster' instead. List all active clusters created by kOps
	@echo "WARNING: 'make list_clusters' is deprecated. Please use 'make list_kops_clusters' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make list_kops_clusters'..."
	@echo ""
	$(MAKE) list_kops_clusters

.PHONY: get_kcfg
get_kcfg: ## DEPRECATED: Use 'make export_kops_kubeconfig' instead.
	@echo "WARNING: 'make create' is deprecated. Please use 'make export_kops_kubeconfig' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make export_kops_kubeconfig'..."
	@echo ""
	$(MAKE) export_kops_kubeconfig $(if $(CLUSTER_NAME),CLUSTER_NAME=$(CLUSTER_NAME))

.PHONY: delete
delete: ## DEPRECATED: Use 'make destroy_kops_cluster' instead. Deletes a single cluster
	@echo "WARNING: 'make delete' is deprecated. Please use 'make destroy_kops_cluster' instead."
	@echo "This command will be removed in a future version."
	@echo "Executing 'make destroy_kops_cluster'..."
	@echo ""
	$(MAKE) destroy_kops_cluster $(if $(CLUSTER_NAME),CLUSTER_NAME=$(CLUSTER_NAME))
