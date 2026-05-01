UV = $(shell which uv)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: deps
deps: ## Installs dependencies
	$(UV) sync
	$(UV) run ansible-galaxy install -r requirements.yaml --force

.PHONY: lint
lint: ## Lints files
	$(UV) run ansible-lint

.PHONY: pre-commit-hooks
pre-commit-hooks: ## Installs pre-commit hooks
	$(UV) run pre-commit install
	$(UV) run pre-commit install --hook-type commit-msg --hook-type pre-push

.PHONY: update-secrets-baseline
update-secrets-baseline: ## Updates the baseline secret file
	$(UV) run detect-secrets scan --update .secrets.baseline
