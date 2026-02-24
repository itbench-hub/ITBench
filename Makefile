# Makefile to run Ansible playbooks

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: deps
deps: ## Installs dependencies
	uv sync
	uv run ansible-galaxy install -r requirements.yaml --force

.PHONY: pre-commit-hooks
pre-commit-hooks: ## Installs pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg --hook-type pre-push
