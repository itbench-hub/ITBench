UV = $(shell which uv)

CLUSTER_NAME_PREFIX  ?= itbench-dev
ENVIRONMENTS_COUNT   ?= 1

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: lint
lint: ## Lints files
	$(UV) run ansible-lint

.PHONY: group-vars
group-vars: ## Generates the group variables from templates
	echo "---\nansible_python_interpreter: $(shell $(UV) python find)" > inventory/group_vars/all/python.yaml
	cp inventory/group_vars/all/aws.yaml.example inventory/group_vars/all/aws.yaml
	cp inventory/group_vars/all/cluster.yaml.example inventory/group_vars/all/cluster.yaml
	cp inventory/group_vars/all/docker.yaml.example inventory/group_vars/all/docker.yaml
	cp inventory/group_vars/all/ssh_keys.yaml.example inventory/group_vars/all/ssh_keys.yaml

.PHONY: create-environment-cluster
create-environment-cluster: ## Creates a single kops cluster on AWS
	$(UV) run ansible-playbook -i inventory playbooks/check_machine_resources.yaml
	$(UV) run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml \
		--tags "create_clusters" \
		--extra-vars "target=single-cluster" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)"
	$(UV) run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml \
		--tags "create_clusters" \
		--extra-vars "target=single-cluster" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)"

.PHONY: get-cluster-kubeconfig
get-cluster-kubeconfig: ## Exports kubeconfig, configures and writes .env for a single cluster
	$(UV) run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml \
		--tags "export_clusters" \
		--extra-vars "target=single-cluster" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)"
	KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_NAME_PREFIX)-environment-aws.k8s.local) \
		$(UV) run python $(abspath ../../scripts/configure_environment_cluster.py)
	@printf 'K8S_AUTH_KUBECONFIG=%s\n' \
		"$(abspath kubeconfigs/$(CLUSTER_NAME_PREFIX)-environment-aws.k8s.local)" \
		> $(abspath ../../scenarios/sre/.env)
	@echo "Run the following command to access the cluster using kubectl:"
	@echo "export KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_NAME_PREFIX)-environment-aws.k8s.local)"

.PHONY: destroy-environment-cluster
destroy-environment-cluster: ## Deletes a single kops cluster on AWS
	$(UV) run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml \
		--tags "delete_clusters" \
		--extra-vars "target=single-cluster" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)"
	$(UV) run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml \
		--tags "delete_clusters" \
		--extra-vars "target=single-cluster" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)"

.PHONY: create-argo-stack
create-argo-stack: ## Creates an Argo stack on AWS
	$(UV) run ansible-playbook -i inventory playbooks/check_machine_resources.yaml
	$(UV) run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml \
		--tags "create_clusters" \
		--extra-vars "target=argo-stack" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)" \
		--extra-vars "environments_count=$(ENVIRONMENTS_COUNT)"
	$(UV) run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml \
		--tags "create_clusters" \
		--extra-vars "target=argo-stack" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)" \
		--extra-vars "environments_count=$(ENVIRONMENTS_COUNT)"

.PHONY: get-stack-kubeconfigs
get-stack-kubeconfigs: ## Exports kubeconfigs, configures and writes .env for an Argo stack
	$(UV) run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml \
		--tags "export_clusters" \
		--extra-vars "target=argo-stack" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)" \
		--extra-vars "environments_count=$(ENVIRONMENTS_COUNT)"
	$(foreach i,$(shell seq 1 $(ENVIRONMENTS_COUNT)), \
		KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_NAME_PREFIX)-environment-$(i)-aws.k8s.local) \
			$(UV) run python $(abspath ../../scripts/configure_environment_cluster.py);)
	@printf 'K8S_AUTH_KUBECONFIG=%s\n' \
		"$(abspath kubeconfigs/$(CLUSTER_NAME_PREFIX)-orchestrator-aws.k8s.local)" \
		> $(abspath ../../scenarios/sre/.env)
	$(UV) run ansible-playbook -i inventory playbooks/sync_group_variables.yaml \
		--extra-vars "target=argo-stack" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)" \
		--extra-vars "environments_count=$(ENVIRONMENTS_COUNT)" \
		--extra-vars "scenarios_group_variables_directory=$(abspath ../../scenarios/sre/inventory/group_vars/orchestrator)"
	cd ../../ && $(UV) run ansible-lint scenarios/sre/inventory/group_vars/orchestrator --fix
	@echo "Run the following command to access the orchestrator cluster using kubectl:"
	@echo "export KUBECONFIG=$(abspath kubeconfigs/$(CLUSTER_NAME_PREFIX)-orchestrator-aws.k8s.local)"

.PHONY: destroy-argo-stack
destroy-argo-stack: ## Destroys an Argo stack on AWS
	$(UV) run ansible-playbook -i inventory playbooks/manage_kops_clusters.yaml \
		--tags "delete_clusters" \
		--extra-vars "target=argo-stack" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)" \
		--extra-vars "environments_count=$(ENVIRONMENTS_COUNT)"
	$(UV) run ansible-playbook -i inventory playbooks/manage_aws_resources.yaml \
		--tags "delete_clusters" \
		--extra-vars "target=argo-stack" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)" \
		--extra-vars "environments_count=$(ENVIRONMENTS_COUNT)"

.PHONY: install-cluster-docker-registry
install-cluster-docker-registry: ## Installs docker registry into single cluster
	$(UV) run ansible-playbook -i inventory playbooks/install_docker_registry.yaml \
		--extra-vars "target=single-cluster" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)"

.PHONY: install-stack-docker-registry
install-stack-docker-registry: ## Installs docker registry into Argo stack clusters
	$(UV) run ansible-playbook -i inventory playbooks/install_docker_registry.yaml \
		--extra-vars "target=argo-stack" \
		--extra-vars "name_prefix=$(CLUSTER_NAME_PREFIX)" \
		--extra-vars "environments_count=$(ENVIRONMENTS_COUNT)"

.PHONY: list-clusters
list-clusters: ## Lists all active clusters
	$(UV) run ansible-playbook -i inventory playbooks/list_kops_clusters.yaml

.PHONY: validate-cluster
validate-cluster: ## Displays the validation status of a cluster
ifdef CLUSTER_NAME
	$(UV) run ansible-playbook -i inventory playbooks/validate_kops_cluster.yaml \
		--extra-vars "kops_cluster_name=$(CLUSTER_NAME)"
else
	@echo "Missing CLUSTER_NAME argument. Please run this command with this variable."
endif

.PHONY: fix-cluster
fix-cluster: ## Attempts to fix a failing cluster
ifdef CLUSTER_NAME
	$(UV) run ansible-playbook -i inventory playbooks/fix_kops_cluster.yaml \
		--extra-vars "kops_cluster_name=$(CLUSTER_NAME)"
else
	@echo "Missing CLUSTER_NAME argument. Please run this command with this variable."
endif
