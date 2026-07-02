MINIKUBE = $(shell which minikube)
UV = $(shell which uv)

MINIKUBE_KUBEADM_CONFIG_FLAGS = --extra-config=kubelet.server-tls-bootstrap=true \
	--extra-config=kube-proxy.metrics-bind-address=0.0.0.0:10249 \
	--extra-config=controller-manager.bind-address=0.0.0.0 \
	--extra-config=controller-manager.authorization-always-allow-paths=/metrics \
	--extra-config=scheduler.bind-address=0.0.0.0 \
	--extra-config=scheduler.authorization-always-allow-paths=/metrics \
	--extra-config=etcd.listen-metrics-urls=http://0.0.0.0:2381

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: lint
lint: ## Lints files
	$(UV) run ansible-lint

.PHONY: group-vars
group-vars: ## Generates the group variables
	mkdir -p inventory/group_vars/all
	echo "ansible_python_interpreter: $(shell $(UV) python find)" > inventory/group_vars/all/ansible.yaml

.PHONY: create-simple-cluster
create-simple-cluster: group-vars ## Creates Minikube cluster for local development
	$(UV) run ansible-playbook -i inventory playbooks/check_machine_resources.yaml \
		--extra-vars "target=single-cluster"
	$(MINIKUBE) start -p minikube-dev $(MINIKUBE_KUBEADM_CONFIG_FLAGS)

.PHONY: start-simple-tunnel
start-simple-tunnel: ## Opens Minikube tunnel to allow external IP access to dev cluster
	$(MINIKUBE) -p minikube-dev tunnel

.PHONY: destroy-simple-cluster
destroy-simple-cluster: ## Deletes the local development Minikube cluster
	-sudo pkill -f "minikube.*minikube-dev.*tunnel"
	$(MINIKUBE) delete -p minikube-dev
	sudo $(MINIKUBE) tunnel --cleanup

.PHONY: create-awx-cluster
create-awx-cluster: group-vars ## Create a Minikube cluster for local development on AWX
	$(UV) run ansible-playbook -i inventory playbooks/check_machine_resources.yaml \
		--extra-vars "target=awx-stack"
	$(MINIKUBE) start -p minikube-awx $(MINIKUBE_KUBEADM_CONFIG_FLAGS)

.PHONY: start-awx-tunnel
start-awx-tunnel: ## Opens Minikube tunnel to allow external IP access to AWX cluster
	$(MINIKUBE) -p minikube-awx tunnel

.PHONY: destroy-awx-cluster
destroy-awx-cluster: ## Deletes the local development AWX Minikube cluster
	-sudo pkill -f "minikube.*minikube-awx.*tunnel"
	$(MINIKUBE) delete -p minikube-awx
	sudo $(MINIKUBE) tunnel --cleanup
