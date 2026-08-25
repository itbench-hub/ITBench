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
	$(UV) run scripts/generate_library_indexes.py \
		--templates_directory=$(abspath ./templates/library/indexes) \
		--library_index_directory=$(abspath ./library/indexes) \
		--playbooks_directory=$(abspath ./scenarios/sre/project)
	$(UV) run scripts/generate_library_index_schemas.py \
		--library_index_directory=$(abspath ./library/indexes) \
		--schemas_directory=$(abspath ./schemas/json) \
		--templates_directory=$(abspath ./templates/schemas/json/library/index)
	$(UV) run scripts/generate_library_specs.py \
		--templates_directory=$(abspath ./templates/library/specs/scenarios) \
		--library_index_directory=$(abspath ./library/indexes) \
		--specs_directory=$(abspath ./library/specs/scenarios)
	$(UV) run scripts/generate_library_readmes.py \
		--templates_directory=$(abspath ./templates/documentation/library) \
		--library_index_directory=$(abspath ./library/indexes) \
		--documentation_directory=$(abspath ./documentation/library)

.PHONY: validate-library
validate-library: ## Validates library indexes
	$(UV) run scripts/validate_library_indexes.py \
		--library_index_directory=$(abspath ./library/indexes) \
		--schemas_directory=$(abspath ./schemas/json)

.PHONY: update-secrets-baseline
update-secrets-baseline: ## Updates the baseline secret file
	$(UV) run detect-secrets scan --update .secrets.baseline

.PHONY: test-scripts
test-scripts: ## Runs unit tests for scripts/
	$(UV) run pytest tests/scripts/
