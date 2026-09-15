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

.PHONY: generate-library
generate-library: ## Generates library indexes, schemas, documentation, and spec files
	$(UV) run library generate all

.PHONY: validate-library
validate-library: ## Validates library indexes
	$(UV) run library validate

.PHONY: scaffold-fault
scaffold-fault: ## Scaffold a new fault index stub
	$(UV) run library scaffold fault

.PHONY: scaffold-scenario
scaffold-scenario: ## Scaffold a new scenario index stub
	$(UV) run library scaffold scenario

.PHONY: update-secrets-baseline
update-secrets-baseline: ## Updates the baseline secret file
	$(UV) run detect-secrets scan --update .secrets.baseline

.PHONY: test-unit
test-unit: ## Runs unit tests
	$(UV) run pytest tests/unit/

.PHONY: test-integration
test-integration: ## Runs all integration tests (requires a live Kubernetes cluster)
	$(UV) run pytest tests/integration/ -m integration
