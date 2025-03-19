help:
	@echo "Makefile commands:"
	@echo "deploy_bundle -- [onetime] deploys the bundle to the cluster"
	@echo "inject_fault -- [onetime] define a new policy (policies) and enable fault for hitting CIS Benchmark controls"
	@echo "destroy_bundle -- [onetime] destroy the target environment"
	@echo "revert_bundle -- [onetime] revert the target environment"
	@echo "get -- [onetime] get status and evaluation"
	@echo "get_status -- [onetime] get status"
	@echo "evaluate -- [onetime] evaluate"
	@echo "Option FOREGROUND=true for synchronous execution. Default execute as background job."
	@echo "Option INPUT_FILE=<path to bundle input file>"
	@echo "help   - Display this help information"

export WORK_DIR = /tmp/scenario

INPUT_FILE ?=
DEFAULT_INPUT_FILE := input.json
PASSED_INPUT_FILE := $(WORK_DIR)/input.json
export BUNDLE_INPUT_FILE := $(PASSED_INPUT_FILE)

# parameters to replace default input.json 
KUBECONFIG :=
SHARED_WORKSPACE :=
JQ_UPDATE_TEMPLATE = if [ -n "$(1)" ]; then \
  jq --arg key_value "$(1)" '.$(2) = $$key_value' $(PASSED_INPUT_FILE) > tmp.json && mv tmp.json $(PASSED_INPUT_FILE) ;\
fi

ifeq ($(FOREGROUND), true)
	REDIRECT := 
	BG := 
else
	REDIRECT := &> $$WORK_DIR/$(LOG_FILE)
	BG := &
endif

ifeq ($(TEST), true)
	PLAYBOOK_DIR := ./stubs
else
	PLAYBOOK_DIR := ./playbooks
endif

prepare_directory:
	@mkdir -p "$(WORK_DIR)"
	@if [ -z "$(INPUT_FILE)" ]; then \
	  echo "Using default input file with override by parameters" 1>&2;\
	  cp $(DEFAULT_INPUT_FILE) $(PASSED_INPUT_FILE) ;\
	  $(call JQ_UPDATE_TEMPLATE,$(KUBECONFIG),kubeconfig);\
	  $(call JQ_UPDATE_TEMPLATE,$(SHARED_WORKSPACE),shared_workspace);\
	else \
	  echo "Using provided input file" 1>&2;\
		cp $(INPUT_FILE) $(PASSED_INPUT_FILE) ;\
  fi

deploy_bundle: prepare_directory
	@cat status.template.json > $$WORK_DIR/status.json
	@$(MAKE) run_playbook LOG_FILE=deploy.log PLAYBOOK=deploy.yml

inject_fault: prepare_directory
	@$(MAKE) run_playbook LOG_FILE=execute.log PLAYBOOK=execute.yml

destroy_bundle: prepare_directory
	@$(MAKE) run_playbook LOG_FILE=destroy.log PLAYBOOK=destroy.yml

remove_fault: prepare_directory
	@$(MAKE) run_playbook LOG_FILE=remove.log PLAYBOOK=fault_removal.yml

revert: prepare_directory
	@$(MAKE) run_playbook LOG_FILE=revert.log PLAYBOOK=revert.yml

evaluate: prepare_directory
	@$(MAKE) run_playbook BG="" REDIRECT="" LOG_FILE=evaluate.log PLAYBOOK=evaluate.yml EXTRA_VARS="--extra-vars \"path_to_output=$(WORK_DIR)/evaluation.json\"" 1>&2; \
	cat $(WORK_DIR)/evaluation.json

run_playbook: EXTRA_VARS ?=
run_playbook: prepare_directory
	@echo "ansible-playbook $(PLAYBOOK_DIR)/$(PLAYBOOK) $(EXTRA_VARS) $(REDIRECT) $(BG)"
	@ansible-playbook $(PLAYBOOK_DIR)/$(PLAYBOOK) $(EXTRA_VARS) $(REDIRECT) $(BG)

get: prepare_directory
	@$(MAKE) run_playbook BG="" REDIRECT="" LOG_FILE=goal.log PLAYBOOK=goal.yml EXTRA_VARS="--extra-vars \"path_to_output=$(WORK_DIR)/goal.json \"" 1>&2
	@jq -s '{metadata: .[0]}' info.json | jq .goal_template=input.goal - $$WORK_DIR/goal.json | jq .vars=input.vars - $$WORK_DIR/goal.json

get_status: prepare_directory
	@cat $$WORK_DIR/status.json