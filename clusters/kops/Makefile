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

.PHONY: check-awx-clusters
check-awx-clusters: ## Check which AWX clusters have validation errors
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

.PHONY: debug-cluster
debug-cluster: ## Debug a failed cluster (usage: CLUSTER_NAME=my-cluster.k8s.local make debug-cluster)
	@if [ -z "$(CLUSTER_NAME)" ]; then \
		echo "Error: CLUSTER_NAME is required"; \
		echo "Usage: CLUSTER_NAME=my-cluster.k8s.local make debug-cluster"; \
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

.PHONY: fix-cluster
fix-cluster: ## Attempt to fix a cluster by removing unjoined nodes (usage: CLUSTER_NAME=my-cluster.k8s.local make fix-cluster)
	@if [ -z "$(CLUSTER_NAME)" ]; then \
		echo "Error: CLUSTER_NAME is required"; \
		echo "Usage: CLUSTER_NAME=my-cluster.k8s.local make fix-cluster"; \
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
