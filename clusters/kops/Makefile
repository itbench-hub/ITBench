# Makefile to run Ansible playbooks

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: group-vars
group-vars: ## Generates the group variables from templates
	echo "---\nansible_python_interpreter: $(shell uv python find)" > inventory/group_vars/all/python.yaml
	cp inventory/group_vars/all/aws.yaml.example inventory/group_vars/all/aws.yaml
	cp inventory/group_vars/all/cluster.yaml.example inventory/group_vars/all/cluster.yaml
	cp inventory/group_vars/all/docker.yaml.example inventory/group_vars/all/docker.yaml
	cp inventory/group_vars/all/ssh_keys.yaml.example inventory/group_vars/all/ssh_keys.yaml
	cp inventory/group_vars/awx/stack.yaml.example inventory/group_vars/awx/stack.yaml
	cp inventory/group_vars/basic/runner.yaml.example inventory/group_vars/basic/runner.yaml

.PHONY: create-cluster
create-cluster: ## Creates a single cluster
	uv run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml --tags "create_clusters" \
		--extra-vars "target=single-cluster"
	uv run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml --tags "create_clusters" \
		--extra-vars "target=single-cluster"

.PHONY: get-cluster-kubeconfig
get-cluster-kubeconfig: ## Exports the kubeconfig of a single cluster
	uv run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml --tags "export_clusters" \
		--extra-vars "target=single-cluster"

.PHONY: destroy-cluster
destroy-cluster: ## Deletes a single cluster
	uv run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml --tags "delete_clusters" \
		--extra-vars "target=single-cluster"
	uv run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml --tags "delete_clusters" \
		--extra-vars "target=single-cluster"

.PHONY: create-awx-stack
create-awx-stack: ## Creates an AWX stack
	uv run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml --tags "create_clusters" \
		--extra-vars "target=awx-stack"
	uv run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml --tags "create_clusters" \
		--extra-vars "target=awx-stack"

.PHONY: get-stack-kubeconfigs
get-stack-kubeconfigs: ## Exports the kubeconfigs of all clusters used in an AWX stack
	uv run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml --tags "export_clusters" \
		--extra-vars "target=awx-stack"

.PHONY: destroy-awx-stack
destroy-awx-stack: ## Destroy an AWX stack
	uv run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml --tags "delete_clusters" \
		--extra-vars "target=awx-stack"
	uv run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml --tags "delete_clusters" \
		--extra-vars "target=awx-stack"

.PHONY: list-clusters
list-clusters: ## Lists all active clusters
	uv run ansible-playbook -i inventory playbooks/list_kops_clusters.yaml

.PHONY: validate-cluster
validate-cluster: ## Displays the validation status of a cluster
ifdef CLUSTER_NAME
	uv run ansible-playbook -i inventory playbooks/validate_kops_cluster.yaml \
		--extra-vars "kops_cluster_name=$(CLUSTER_NAME)"
else
	@echo "Missing CLUSTER_NAME argument. Please run this command with this variable."
endif

.PHONY: fix-cluster
fix-cluster: ## Attempts to fix a failing cluster
ifdef CLUSTER_NAME
	uv run ansible-playbook -i inventory playbooks/fix_kops_cluster.yaml \
		--extra-vars "kops_cluster_name=$(CLUSTER_NAME)"
else
	@echo "Missing CLUSTER_NAME argument. Please run this command with this variable."
endif
