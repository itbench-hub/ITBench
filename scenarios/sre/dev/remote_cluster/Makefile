# Makefile to run Ansible playbooks

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: group_vars
group_vars: ## Generates the group variables
	mkdir group_vars/all
	echo "ansible_python_interpreter: $(shell uv python find)" > group_vars/all/ansible.yaml
	cp group_vars/development/awx_stack.yaml.example group_vars/development/awx_stack.yaml
	cp group_vars/development/kops_cluster.yaml.example group_vars/development/kops_cluster.yaml

.PHONY: create_kops_cluster
create_kops_cluster: ## Creates a single cluster created by kops
	uv run ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "create_cluster"

.PHONY: list_kops_clusters
list_kops_clusters: ## Lists all active clusters created by kops
	uv run ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "list_clusters"

.PHONY: export_kops_kubeconfig
export_kops_kubeconfig: ## Exports the kubeconfig of a single cluster created by kops
ifdef CLUSTER_NAME
	uv run ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "export_cluster" \
		--extra-vars "kops_full_cluster_name_override=$(CLUSTER_NAME)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "export_cluster"
endif

.PHONY: destroy_kops_cluster
destroy_kops_cluster: ## Deletes a single cluster created by kops
ifdef CLUSTER_NAME
	uv run ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "delete_cluster" \
		--extra-vars "kops_full_cluster_name_override=$(CLUSTER_NAME)"
else
	uv run ansible-playbook -i inventory.yaml playbooks/manage_kops_cluster.yaml --tags "delete_cluster"
endif

.PHONY: create_awx_stack
create_awx_stack: ## Creates an AWX stack created by kops
	uv run ansible-playbook -i inventory.yaml playbooks/manage_awx_stack.yaml --tags "create_stack"

.PHONY: export_awx_kubeconfigs
export_awx_kubeconfigs: ## Exports the kubeconfigs of all clusters used in an AWX stack
	uv run ansible-playbook -i inventory.yaml playbooks/manage_awx_stack.yaml --tags "export_stack"

.PHONY: destroy_awx_stack
destroy_awx_stack: ## Destroy an AWX stack created by kops
	uv run ansible-playbook -i inventory.yaml playbooks/manage_awx_stack.yaml --tags "delete_stack"

.PHONY: check_awx_clusters
check_awx_clusters: ## Check which AWX clusters have validation errors
	@echo "Reading configuration..."
	@BUCKET=$$(grep 'bucket_name:' group_vars/development/kops_cluster.yaml | awk '{print $$2}' | tr -d '"'); \
	PREFIX=$$(grep 'name_prefix:' group_vars/development/awx_stack.yaml | head -1 | awk '{print $$2}'); \
	echo "Checking clusters: $$PREFIX* (state: s3://$$BUCKET)"; \
	echo ""; \
	CLUSTERS=$$(kops get clusters --state=s3://$$BUCKET -o json 2>/dev/null | \
		python3 -c "import sys, json; [print(c['metadata']['name']) for c in json.load(sys.stdin) if '$$PREFIX' in c['metadata']['name']]" 2>/dev/null); \
	for cluster in $$CLUSTERS; do \
		printf "%-60s " "$$cluster:"; \
		kops validate cluster --name=$$cluster --state=s3://$$BUCKET --wait=0s >/dev/null 2>&1 \
			&& echo "✓ OK" || echo "✗ FAILED"; \
	done

.PHONY: debug_cluster
debug_cluster: ## Debug a failed cluster (usage: CLUSTER_NAME=my-cluster.k8s.local make debug_cluster)
	@if [ -z "$(CLUSTER_NAME)" ]; then \
		echo "Error: CLUSTER_NAME is required"; \
		echo "Usage: CLUSTER_NAME=my-cluster.k8s.local make debug_cluster"; \
		exit 1; \
	fi
	@BUCKET=$$(grep 'bucket_name:' group_vars/development/kops_cluster.yaml | awk '{print $$2}' | tr -d '"'); \
	echo "=== Cluster Validation Details ==="; \
	kops validate cluster --name=$(CLUSTER_NAME) --state=s3://$$BUCKET --wait=0s || true; \
	echo ""; \
	echo "=== Exporting Kubeconfig ==="; \
	kops export kubecfg --name=$(CLUSTER_NAME) --state=s3://$$BUCKET --admin --kubeconfig=/tmp/debug-$(CLUSTER_NAME).yaml 2>&1 || true; \
	echo ""; \
	echo "=== Node Status ==="; \
	kubectl get nodes --kubeconfig=/tmp/debug-$(CLUSTER_NAME).yaml 2>&1 || echo "Failed to get nodes"; \
	echo ""; \
	echo "=== Non-Running Pods ==="; \
	kubectl get pods --all-namespaces --kubeconfig=/tmp/debug-$(CLUSTER_NAME).yaml 2>&1 | grep -v "Running\|Completed" || echo "All pods are running"

.PHONY: fix_cluster
fix_cluster: ## Attempt to fix a cluster by removing unjoined nodes (usage: CLUSTER_NAME=my-cluster.k8s.local make fix_cluster)
	@if [ -z "$(CLUSTER_NAME)" ]; then \
		echo "Error: CLUSTER_NAME is required"; \
		echo "Usage: CLUSTER_NAME=my-cluster.k8s.local make fix_cluster"; \
		exit 1; \
	fi
	@BUCKET=$$(grep 'bucket_name:' group_vars/development/kops_cluster.yaml | awk '{print $$2}' | tr -d '"'); \
	REGION=$$(grep 'region:' group_vars/development/kops_cluster.yaml | head -1 | awk '{print $$2}'); \
	echo "Detecting problematic instances..."; \
	INSTANCE_IDS=$$(kops validate cluster --name=$(CLUSTER_NAME) --state=s3://$$BUCKET --wait=0s 2>&1 | \
		grep "has not yet joined cluster" | \
		grep -o "i-[a-z0-9]*" | sort -u | tr '\n' ' '); \
	if [ -z "$$INSTANCE_IDS" ]; then \
		echo "No unjoined instances found. Cluster might be healthy or have different issues."; \
		exit 1; \
	fi; \
	COUNT=$$(echo $$INSTANCE_IDS | wc -w); \
	echo "Found $$COUNT problematic instance(s): $$INSTANCE_IDS(region: $$REGION)"; \
	echo ""; \
	echo "Terminating $$COUNT instance(s): $$INSTANCE_IDS"; \
	AWS_PAGER="" aws ec2 terminate-instances --instance-ids $$INSTANCE_IDS --region $$REGION; \
	echo ""; \
	echo "Waiting for AWS Auto Scaling to create replacement(s) (5 minutes)..."; \
	sleep 300; \
	echo ""; \
	echo "=== Validating cluster ==="; \
	kops validate cluster --name=$(CLUSTER_NAME) --state=s3://$$BUCKET --wait=5m || echo "Cluster still has issues, may need more time"

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
