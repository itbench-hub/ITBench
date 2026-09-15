---
name: fault-scaffolding
description: |
  Assists with creating new fault mechanisms for ITBench scenarios, from incident
  description through Ansible implementation. Guides brainstorming, service selection,
  and code implementation consistent with existing fault patterns.
---

# Purpose

This skill guides you through the complete fault creation workflow:

1. **Incident Analysis** - Understanding the IT incident to reproduce
2. **Application Brainstorming** - Mapping incident to available applications
3. **Service Selection** - Identifying target services/components
4. **Ansible Implementation** - Writing fault injection code

# When to Use This Skill

This skill auto-activates when:

- Working with files matching `**/templates/library/indexes/faults/*.yaml.j2`
- Editing files in `**/faults/tasks/inject_*.yaml`
- User mentions "fault scaffold", "new fault", "incident", "reproduce fault"
- Creating or modifying fault definitions

# Workflow

## Step 0: Check for Existing TODOs or Create Scaffolding

**First, check if there are existing fault TODOs:**

If TODOs exist → Skip to Step 4 to complete them.
If NO TODOs exist → Create new fault scaffolding (Steps 1-3).

## Step 1: Incident Description & Fault Input Collection

### 1.0 Check for Similar Existing Faults

**IMPORTANT**: Before creating a new fault, always check if a similar fault already exists.

**Search existing fault index files:**

1. **List all fault index files:**
   ```bash
   ls library/indexes/faults/
   ```

2. **Search fault indexes by keyword:**
   ```bash
   grep -rl "configmap\|image\|network\|memory" library/indexes/faults/
   ```

3. **Search by name field:**
   ```bash
   grep -h '"name"' library/indexes/faults/*.json | sort
   ```

4. **List all fault injection tasks:**
   ```bash
   ls scenarios/sre/project/roles/faults/tasks/inject_*.yaml
   ```

5. **Search fault tasks by pattern:**
   ```bash
   grep -rl "ConfigMap\|Image\|NetworkPolicy" scenarios/sre/project/roles/faults/tasks/
   ```

**If similar fault exists:**
- ✅ **Reuse** the existing fault for your scenario
- ✅ **Reference** the existing implementation pattern
- ✅ **Extend** the existing fault if needed (add new arguments)

**If no similar fault exists:**
- ✅ Proceed with creating a new fault

### 1.1 Gather Incident Information

**Ask the user to provide:**
- Link to incident documentation (Jira, GitHub issue, etc.), OR
- Written description of the IT incident/problem

**Extract key information:**
- What is failing? (service, pod, connection, etc.)
- What observable symptoms? (high latency, errors, pod crashes, etc.)
- What is the root cause? (misconfiguration, resource exhaustion, network issue, etc.)

### 1.2 Collect Fault Details

Run the scaffold command from the **root directory** to create the stub interactively:

```bash
make scaffold-fault
```

This prompts for:
1. **Fault Name** - Human-readable name
   - Example: "Nonexistent Kubernetes Workload Container Image"

2. **Fault Description** - Technical explanation of the mechanism
   - Example: "This fault injects a nonexistent image into a designated Kubernetes workload's container."

3. **Fault Expectation** - Observable behavior when fault is active
   - Example: "The faulted pod(s) will enter the `Pending` state due to an `ImagePullBackOff` error."

The script writes a new `templates/library/indexes/faults/<N>.yaml.j2` stub.

### 1.3 Understand the Stub Structure

**Read the fault schema to understand required fields:**
```bash
cat schemas/json/library/index/fault.json
```

**Check available tags from the schema:**
```bash
jq '.properties.tags.items.enum' schemas/json/library/index/fault.json
```

**Check available alert types:**
```bash
jq '.properties.alerts.properties.application.items.enum' schemas/json/library/index/fault.json
jq '.properties.alerts.properties.goldenSignal.items.enum' schemas/json/library/index/fault.json
```

The generated stub in `templates/library/indexes/faults/<N>.yaml.j2` will have empty fields to complete:
```yaml
alerts: {}
arguments:
  jsonSchema: {}
name: <fault name from prompt>
description: <fault description from prompt>
expectation: <fault expectation from prompt>
platform: ""
resources: []
solutions:
  templates: []
tags: []
```

## Step 2: Brainstorm Implementation

**Read available applications from:**
```bash
cat scenarios/sre/project/roles/applications/vars/main/releases.yaml
```

This yields the application keys, names, and namespaces:
```yaml
applications_releases:
  book_info:
    name: book-info
    namespace: book-info
  opentelemetry_demo:
    name: otel-demo
    namespace: otel-demo
```

For documentation URLs, consult `library/indexes/applications/`:
```bash
jq '{id, name, resources}' library/indexes/applications/1.json
jq '{id, name, resources}' library/indexes/applications/2.json
```

**Application Preference:**
- **Prefer OpenTelemetry Demo** (`opentelemetry_demo` / `otel-demo`) for most scenarios — it's richer, more comprehensive, and better maintained
- Use BookInfo (`book_info` / `book-info`) only if the fault specifically requires its simpler architecture

**Brainstorm questions:**
1. Which application best represents this incident scenario?
2. What Kubernetes resources would be affected? (Deployment, Service, ConfigMap, NetworkPolicy, etc.)
3. What changes would reproduce the incident? (image change, env var modification, resource limits, etc.)
4. Reference similar faults checked in Step 1.0 for implementation patterns

## Step 3: Identify Target Services

### 3.1 Get application namespace from releases.yaml
```bash
grep -A 3 "opentelemetry_demo:" scenarios/sre/project/roles/applications/vars/main/releases.yaml
# namespace: otel-demo

grep -A 3 "book_info:" scenarios/sre/project/roles/applications/vars/main/releases.yaml
# namespace: book-info
```

### 3.2 Discover services from Kubernetes templates
```bash
NAMESPACE="otel-demo"  # or book-info

# Find all Deployments
grep -r "kind: Deployment" scenarios/sre/project/roles/applications/templates/kubernetes/ | grep "$NAMESPACE"

# Find all Services
grep -r "kind: Service" scenarios/sre/project/roles/applications/templates/kubernetes/ | grep "$NAMESPACE"
```

### 3.3 Fetch service architecture from documentation (REQUIRED)

Using the `resources` URLs from `library/indexes/applications/2.json` (OpenTelemetry Demo):
1. Navigate to the documentation URL (e.g., `https://opentelemetry.io/docs/demo/architecture/`)
2. **Study the architecture diagram** — critical for understanding service dependencies
3. Identify available services and their roles

### 3.4 Optional: Ground in Real Deployment

**Ask the user:**
> Would you like to deploy the application to a live cluster to get actual deployment names? This requires a running Kubernetes cluster.

**If YES:**
```bash
# From scenarios/sre/
export KUBECONFIG=<path-from-user>
make deploy-tools
make deploy-applications

# Query live cluster
kubectl get deployments -n otel-demo -o jsonpath='{.items[*].metadata.name}'
kubectl get services -n otel-demo -o jsonpath='{.items[*].metadata.name}'
kubectl get pods -n otel-demo --show-labels
```

**If NO:** Continue with template-based discovery from Step 3.2

### 3.5 Identify target service
**Consider:**
- Which service exhibits the problem?
- Which service is the root cause?
- Are multiple services affected?

## Step 4: Write Ansible Implementation

Create the injection task file following patterns from existing faults.

### File Location
`scenarios/sre/project/roles/faults/tasks/inject_<fault-id with underscores>.yaml`

**IMPORTANT**: File naming uses **underscores only** (e.g., `inject_my_fault_name.yaml`), derived from the fault's `id` field with hyphens replaced by underscores.

### Resource Naming Guidelines

**CRITICAL:**
- **DO NOT** create new resources with names that reveal the fault mechanism
- **DO NOT** use names like `fault-injector`, `chaos-config`, `memory-leak-pod`
- **DO** use neutral, application-appropriate names that blend in
- **GOOD**: `app-config`, `sidecar-processor`, `cache-helper`
- **BAD**: `fault-config`, `crash-trigger`, `latency-injector`

**Rationale**: The agent solving scenarios should diagnose the issue based on symptoms, not by discovering obviously-named fault injection resources.

### Standard Pattern

```yaml
---
# Brief description of what this fault does

# Step 1: Retrieve and validate target resource
- name: Retrieve [resource-type]
  kubernetes.core.k8s_info:
    kubeconfig: "{{ faults_cluster.kubeconfig }}"
    api_version: "{{ injection_task.args.kubernetesObject.apiVersion }}"
    kind: "{{ injection_task.args.kubernetesObject.kind }}"
    name: "{{ injection_task.args.kubernetesObject.metadata.name }}"
    namespace: "{{ injection_task.args.kubernetesObject.metadata.namespace }}"
  register: faults_workload

- name: Validate that [resource-type] exists
  ansible.builtin.assert:
    that:
      - faults_workload.api_found
      - faults_workload.resources | ansible.builtin.length == 1
    fail_msg: Unable to find [resource-type]
    success_msg: Found [resource-type]

# Step 2: Inject the fault (varies by fault type)

# Step 3: Wait for fault manifestation
- name: Wait for [resource-type] to update
  kubernetes.core.k8s_info:
    api_version: "{{ faults_workload.resources[0].apiVersion }}"
    kubeconfig: "{{ faults_cluster.kubeconfig }}"
    kind: "{{ faults_workload.resources[0].kind }}"
    name: "{{ faults_workload.resources[0].metadata.name }}"
    namespace: "{{ faults_workload.resources[0].metadata.namespace }}"
  register: faults_patched_workload
  until:
    - faults_patched_workload.api_found
    - faults_patched_workload.resources | ansible.builtin.length == 1
    # Add appropriate conditions for this fault type
  delay: 15
  retries: 20
```

### Discover Existing Fault Patterns Dynamically

```bash
# List all existing injection tasks
ls scenarios/sre/project/roles/faults/tasks/inject_*.yaml | sort

# Find by fault category
grep -rl "image:" scenarios/sre/project/roles/faults/tasks/inject_*.yaml
grep -rl "ConfigMap\|environment" scenarios/sre/project/roles/faults/tasks/inject_*.yaml
grep -rl "ResourceQuota\|limits\|requests" scenarios/sre/project/roles/faults/tasks/inject_*.yaml
grep -rl "NetworkPolicy" scenarios/sre/project/roles/faults/tasks/inject_*.yaml
grep -rl "chaos-mesh.org" scenarios/sre/project/roles/faults/tasks/inject_*.yaml

# Count steps to gauge complexity
for f in scenarios/sre/project/roles/faults/tasks/inject_*.yaml; do
  echo "$(grep -c '^- name:' "$f") steps: $(basename "$f")"
done | sort -n
```

### Important Implementation Notes

1. **Always add ITBench label**: `app.kubernetes.io/managed-by: ITBench` to created resources
2. **Use registered variable**: Access original resource as `faults_workload.resources[0]`
3. **Validate before modifying**: Assert resource exists
4. **Wait for manifestation**: Use `k8s_info` with `until` conditions
5. **Reference similar faults**: Search existing tasks for patterns

## Completing the Fault Index Template

After implementing the Ansible task, complete the fault entry in:
**File**: `templates/library/indexes/faults/<N>.yaml.j2`

### Step 1: Verify Required Fields from Schema

```bash
jq '.required' schemas/json/library/index/fault.json
jq '.properties | keys' schemas/json/library/index/fault.json
```

### Step 2: Discover Argument Schema Patterns from Existing Faults

```bash
# View a specific fault's argument schema
jq '.arguments' library/indexes/faults/1.json

# Find all unique required-argument patterns
jq -s '[.[].arguments.jsonSchema.required] | unique' library/indexes/faults/*.json

# Find faults with kubernetesObject + container pattern
grep -l '"container"' library/indexes/faults/*.json
```

### Step 3: Discover Alert Types

```bash
# Available alert enums
jq '.properties.alerts.properties.application.items.enum' schemas/json/library/index/fault.json
jq '.properties.alerts.properties.goldenSignal.items.enum' schemas/json/library/index/fault.json

# Which existing faults use which alerts
jq -s '.[] | select(.alerts.application[]? == "KubePodCrashLooping") | .id' library/indexes/faults/*.json
```

### Step 3.1: Registering New Alerts

**If your fault introduces a NEW alert** (not in the schema enum), register it in THREE locations:

1. **Fault Schema** — add to alert enum:
   ```bash
   # Edit: schemas/json/library/index/fault.json
   # Add to: .properties.alerts.properties.application.items.enum
   ```

2. **Alerts Monitoring Playbook** — add to alert detection (3 locations):
   ```bash
   # Edit: scenarios/sre/project/playbooks/check_for_specific_alerts_in_firing_state.yaml
   ```

3. **PrometheusRules Template** — define the actual alert rule:
   ```bash
   # OpenTelemetry Demo:
   scenarios/sre/project/roles/applications/templates/kubernetes/otel_demo/prometheusrules.j2
   # BookInfo:
   scenarios/sre/project/roles/applications/templates/kubernetes/book_info/prometheusrules.j2
   ```

### Step 4: Discover Solution Patterns

```bash
# View a similar fault's solutions
jq '.solutions' library/indexes/faults/1.json

# Find all unique solution commands
jq -rs '[.[].solutions.templates[].steps[].command? // empty] | unique' library/indexes/faults/*.json
```

### Step 5: Use a Similar Fault as Template

```bash
# Find the most similar fault by name keyword
grep -hl '"ConfigMap"\|"Image"' library/indexes/faults/*.json

# Read a full fault entry as a reference
cat library/indexes/faults/3.json
```

## After Completing the Template

Run from the **root directory**:

```bash
make generate-library    # renders templates → library/indexes/ and documentation/
make validate-library    # validates all index JSON against schemas
```

Then from `scenarios/sre/`:

```bash
make generate-resource-files   # generates Ansible role files (argument_specs, task_files vars, task stubs)
```

# Reference Examples — Discover Dynamically

```bash
# Find simple faults (fewest task steps)
for f in scenarios/sre/project/roles/faults/tasks/inject_*.yaml; do
  echo "$(grep -c '^- name:' "$f") $(basename "$f")"
done | sort -n | head -10

# Find complex faults
for f in scenarios/sre/project/roles/faults/tasks/inject_*.yaml; do
  echo "$(grep -c '^- name:' "$f") $(basename "$f")"
done | sort -n | tail -10

# Find Chaos Mesh faults
grep -rl "chaos-mesh.org" scenarios/sre/project/roles/faults/tasks/

# Find node-level operations
grep -rl "node\|cordon\|drain" scenarios/sre/project/roles/faults/tasks/
```

# Anti-Patterns

❌ **Don't:**
- Skip brainstorming with available applications
- Guess service names without checking documentation or templates
- Create faults without checking for similar existing ones
- Forget the `app.kubernetes.io/managed-by: ITBench` label
- Use hardcoded namespace/service names in fault index templates (use Jinja2 `{{ args.* }}` variables)
- **Create resources with obvious fault-revealing names**

✅ **Do:**
- Start with incident description
- Map to available applications using `releases.yaml` and `library/indexes/applications/`
- Reference existing similar fault implementations
- Test in a real cluster before finalizing
- Follow consistent Ansible patterns
- Use Jinja2 templates in solutions for reusability
- **Use neutral, application-appropriate names for any new resources**

# Automatic Transition to Scenario Creation

**IMPORTANT**: After completing fault scaffolding, **automatically proceed** to scenario creation using the **scenario-scaffolding** skill.

**Do not wait for user prompt** — transition immediately to:
1. Apply this fault to the identified service/component
2. Populate scenario index template with application, faults, and disruptions
3. Generate groundtruth files with DSL format

This creates a complete end-to-end workflow: **Incident → Fault → Scenario → Ground Truth**
