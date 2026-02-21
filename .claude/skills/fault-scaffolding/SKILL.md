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

- Working with files matching `**/faults/index.json`
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

**Search existing faults:**

1. **Search fault index by keywords:**
   ```bash
   jq '.[] | select(.name | test("(?i)configmap|image|network|memory"))' \
     scenarios/sre/roles/documentation/files/library/faults/index.json
   ```

2. **List all fault injection tasks:**
   ```bash
   ls scenarios/sre/roles/faults/tasks/inject_*.yaml
   ```

3. **Search fault tasks by pattern:**
   ```bash
   grep -r "ConfigMap\|Image\|NetworkPolicy" scenarios/sre/roles/faults/tasks/
   ```

**If similar fault exists:**
- ✅ **Reuse** the existing fault for your scenario
- ✅ **Reference** the existing implementation pattern
- ✅ **Extend** the existing fault if needed (add new arguments)

**If no similar fault exists:**
- ✅ Proceed with creating a new fault

**Why check first?**
- Avoids duplicate faults
- Maintains consistency across scenarios
- Saves implementation time
- Leverages tested fault mechanisms

### 1.1 Gather Incident Information

**Ask the user to provide:**
- Link to incident documentation (Jira, GitHub issue, etc.), OR
- Written description of the IT incident/problem

**Extract key information:**
- What is failing? (service, pod, connection, etc.)
- What observable symptoms? (high latency, errors, pod crashes, etc.)
- What is the root cause? (misconfiguration, resource exhaustion, network issue, etc.)

### 1.2 Collect Fault Details

Gather required information (similar to `scaffolding/tasks/collect_fault_inputs.yaml`):

1. **Fault Name** - Human-readable name
   - Example: "Nonexistent Kubernetes Workload Container Image"

2. **Fault Description** - Technical explanation of the mechanism
   - Example: "This fault injects a nonexistent image into a designated Kubernetes workload's container."

3. **Fault Expectation** - Observable behavior when fault is active
   - Example: "The faulted pod(s) will enter the `Pending` state due to an `ImagePullBackOff` error. The workload will become unable to function."

4. **Tags** - Read available tags from schema file:
   ```bash
   jq '.properties.tags.items.enum' \
     scenarios/sre/roles/documentation/files/library/faults/schema.json
   ```
   Choose the most appropriate tag(s) for the fault mechanism.

5. **Generate Fault ID** - Derive from name (lowercase, kebab-case):
   ```
   fault_id = fault_name.lower().replace(" ", "-").regex_replace("[^a-z0-9-]", "")
   Example: "Nonexistent Kubernetes Workload Container Image"
         → "nonexistent-kubernetes-workload-container-image"
   ```

### 1.3 Create Scaffolding Files

**First, read the fault schema to understand required fields:**
```bash
cat scenarios/sre/roles/documentation/files/library/faults/schema.json
```

**File 1**: `scenarios/sre/roles/documentation/files/library/faults/index.json`

Add new fault entry with fields from schema:
```bash
# Check required fields
jq '.required' scenarios/sre/roles/documentation/files/library/faults/schema.json

# Check properties structure
jq '.properties | keys' scenarios/sre/roles/documentation/files/library/faults/schema.json
```

Create entry matching the schema (required fields: arguments, description, expectation, name, platform, resources, solutions, tags):
```json
{
  "alerts": "TODO",
  "arguments": "TODO",
  "description": "<fault description from user>",
  "expectation": "<fault expectation from user>",
  "id": "<generated-fault-id>",
  "name": "<fault name from user>",
  "platform": "Kubernetes",
  "resources": "TODO",
  "solutions": "TODO",
  "tags": ["<tag from user>"]
}
```

**File 2**: `scenarios/sre/roles/faults/tasks/inject_<fault-id>.yaml`

Create stub injection task:
```yaml
---
# TODO: LLM-generated injection task for <fault name>
- name: Print message
  ansible.builtin.debug:
    msg: This fault injection (<fault-id>) is unimplemented.
```

**Display summary after creation:**
```
✅ Fault scaffolding created!

  Name: <fault name>
  ID: <fault-id>
  Tags: [<tags>]

Files created:
  ✓ faults/index.json (entry added with TODOs)
  ✓ faults/tasks/inject_<fault-id>.yaml (stub created)

Next steps:
  1. Complete TODO fields in fault index (arguments, alerts, resources, solutions)
  2. Implement Ansible injection task
  3. Test fault injection
```

## Step 2: Brainstorm Implementation

**Read available applications dynamically from:**
```bash
cat scenarios/sre/roles/applications/defaults/main/managers.yaml
```

**Extract application details:**
```bash
# List all application keys
grep -E "^  [a-z_]+:" scenarios/sre/roles/applications/defaults/main/managers.yaml | sed 's/://g' | awk '{print $1}'

# For each application key, get full configuration
# Replace <app-key> with the actual application key from the list above
grep -A 15 "^  <app-key>:" scenarios/sre/roles/applications/defaults/main/managers.yaml

# Extract specific fields for an application
grep -A 15 "^  <app-key>:" scenarios/sre/roles/applications/defaults/main/managers.yaml | grep -E "namespace:|url:|documentation:"
```

**For each application found, dynamically extract:**
- Application key/ID
- Kubernetes namespace
- Documentation URL
- Helm chart details (if applicable)

**Brainstorm questions:**
1. Which application best represents this incident scenario?
2. What Kubernetes resources would be affected? (Deployment, Service, ConfigMap, NetworkPolicy, etc.)
3. What changes would reproduce the incident? (image change, env var modification, resource limits, etc.)
4. Reference similar faults checked in Step 1.0 for implementation patterns

## Step 3: Identify Target Services

**Dynamically identify services for the chosen application:**

### 3.1 List all available applications
```bash
# Extract application keys from managers.yaml
grep -E "^  [a-z_]+:" scenarios/sre/roles/applications/defaults/main/managers.yaml | sed 's/://g' | awk '{print $1}'
```

### 3.2 Get application configuration
```bash
# Replace <app-key> with the chosen application key from step 3.1
grep -A 20 "^  <app-key>:" scenarios/sre/roles/applications/defaults/main/managers.yaml
```

### 3.3 Extract metadata
```bash
# Get documentation URL
grep -A 20 "^  <app-key>:" scenarios/sre/roles/applications/defaults/main/managers.yaml | grep -E "url:|documentation:" | head -1

# Get namespace
grep -A 20 "^  <app-key>:" scenarios/sre/roles/applications/defaults/main/managers.yaml | grep "namespace:" | head -1
```

### 3.4 Fetch service architecture from documentation (REQUIRED)
Using the documentation URL from step 3.3:
1. Navigate to the application's documentation URL
2. Look for:
   - Architecture diagrams
   - Service listings
   - Component documentation
   - Deployment guides
3. Identify available services and their roles

### 3.5 Identify target service
**Consider:**
- Which service exhibits the problem?
- Which service is the root cause?
- Are multiple services affected?

## Step 4: Write Ansible Implementation

Create the injection task file following patterns from existing faults.

### File Location
`scenarios/sre/roles/faults/tasks/inject_<fault-id>.yaml`

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
# See examples below

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

### Common Fault Types - Discover Dynamically

**Instead of hardcoded examples, discover existing fault patterns:**

#### Step 1: List All Existing Fault Injection Tasks
```bash
ls scenarios/sre/roles/faults/tasks/inject_*.yaml | sort
```

#### Step 2: Search by Fault Category/Pattern

**Find Image-Related Faults:**
```bash
ls scenarios/sre/roles/faults/tasks/inject_*image*.yaml
grep -l "image:" scenarios/sre/roles/faults/tasks/inject_*.yaml
```

**Find Configuration/ConfigMap Faults:**
```bash
ls scenarios/sre/roles/faults/tasks/inject_*config*.yaml
grep -l "ConfigMap\|environment" scenarios/sre/roles/faults/tasks/inject_*.yaml
```

**Find Resource Faults:**
```bash
ls scenarios/sre/roles/faults/tasks/inject_*resource*.yaml
grep -l "ResourceQuota\|limits\|requests" scenarios/sre/roles/faults/tasks/inject_*.yaml
```

**Find Network Faults:**
```bash
ls scenarios/sre/roles/faults/tasks/inject_*network*.yaml
grep -l "NetworkPolicy" scenarios/sre/roles/faults/tasks/inject_*.yaml
```

**Find Chaos Mesh Faults:**
```bash
ls scenarios/sre/roles/faults/tasks/inject_*chaos*.yaml
grep -l "chaos-mesh.org" scenarios/sre/roles/faults/tasks/inject_*.yaml
```

#### Step 3: Read and Study Relevant Fault Files
```bash
# Read a specific fault to understand its pattern
cat scenarios/sre/roles/faults/tasks/inject_<fault-name>.yaml

# Search for specific Kubernetes resources in faults
grep -r "kind: Deployment" scenarios/sre/roles/faults/tasks/
grep -r "kind: ConfigMap" scenarios/sre/roles/faults/tasks/
grep -r "kind: NetworkPolicy" scenarios/sre/roles/faults/tasks/
```

#### Step 4: Find Faults by Tag
```bash
# Search faults index by tag
jq '.[] | select(.tags[] | contains("Networking"))' scenarios/sre/roles/documentation/files/library/faults/index.json
jq '.[] | select(.tags[] | contains("Performance"))' scenarios/sre/roles/documentation/files/library/faults/index.json
jq '.[] | select(.tags[] | contains("Deployment"))' scenarios/sre/roles/documentation/files/library/faults/index.json
```

#### Step 5: Match Fault Mechanism to Incident
Based on your incident analysis (Step 1), identify which existing faults have similar mechanisms:
- Image issues → search for image-related faults
- Config problems → search for ConfigMap/environment faults
- Network connectivity → search for NetworkPolicy faults
- Resource exhaustion → search for quota/limits faults
- Application crashes → search for code/chaos faults

### Important Implementation Notes

1. **Always add ITBench label**: `app.kubernetes.io/managed-by: ITBench` to created resources
2. **Use registered variable**: Access original resource as `faults_workload.resources[0]`
3. **Validate before modifying**: Assert resource exists
4. **Wait for manifestation**: Use `k8s_info` with `until` conditions
5. **Reference similar faults**: Search existing tasks for patterns

## Completing the Fault Index - Dynamic Discovery

After implementing the Ansible task, complete the fault entry in:
**File**: `scenarios/sre/roles/documentation/files/library/faults/index.json`

### Step 1: Verify Required Fields from Schema

```bash
# Check required fields
jq '.required' scenarios/sre/roles/documentation/files/library/faults/schema.json

# Check all property names and types
jq '.properties | to_entries[] | {key: .key, type: .value.type, required: .value.required}' \
  scenarios/sre/roles/documentation/files/library/faults/schema.json
```

### Step 2: Discover Argument Schema Patterns from Existing Faults

**Find similar faults to use as templates:**
```bash
# Find faults with similar argument structures
jq '.[] | select(.arguments.jsonSchema.required[]? | contains("kubernetesObject")) | {id, required: .arguments.jsonSchema.required}' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# View specific fault's argument schema
jq '.[] | select(.id == "<similar-fault-id>") | .arguments' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# Find all unique argument patterns
jq '[.[] | .arguments.jsonSchema.required] | unique' \
  scenarios/sre/roles/documentation/files/library/faults/index.json
```

**Common patterns discovered:**
```bash
# Workload-only pattern
jq '.[] | select(.arguments.jsonSchema.required == ["kubernetesObject"]) | .id' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# Workload + container pattern
jq '.[] | select(.arguments.jsonSchema.required | contains(["kubernetesObject", "container"])) | .id' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# Custom patterns
jq '.[] | select(.arguments.jsonSchema.required | length > 2) | {id, required: .arguments.jsonSchema.required}' \
  scenarios/sre/roles/documentation/files/library/faults/index.json
```

### Step 3: Discover Alert Types Dynamically

**Get available alert types from schema:**
```bash
# Application alerts enum
jq '.properties.alerts.properties.application.items.enum' \
  scenarios/sre/roles/documentation/files/library/faults/schema.json

# Golden signal alerts enum
jq '.properties.alerts.properties.goldenSignal.items.enum' \
  scenarios/sre/roles/documentation/files/library/faults/schema.json
```

**Find which faults use which alerts:**
```bash
# Find faults with specific alert
jq '.[] | select(.alerts.application[]? == "KubePodCrashLooping") | .id' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# See all alert combinations
jq '[.[] | .alerts] | unique' \
  scenarios/sre/roles/documentation/files/library/faults/index.json
```

### Step 4: Discover Solution Patterns from Existing Faults

**Find common solution templates:**
```bash
# Find faults with rollback solutions
jq '.[] | select(.solutions.templates[].steps[].command? | contains("rollout undo")) | .id' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# View specific fault's solutions
jq '.[] | select(.id == "<similar-fault-id>") | .solutions' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# Find all unique solution patterns
jq '[.[] | .solutions.templates[].steps[].command] | unique' \
  scenarios/sre/roles/documentation/files/library/faults/index.json
```

### Step 5: Use Similar Fault as Template

**Complete workflow:**
```bash
# 1. Find the most similar fault by searching for keywords
jq '.[] | select(.name | contains("ConfigMap") or contains("Image")) | {id, name}' \
  scenarios/sre/roles/documentation/files/library/faults/index.json

# 2. Extract full entry as template
jq '.[] | select(.id == "<similar-fault-id>")' \
  scenarios/sre/roles/documentation/files/library/faults/index.json > /tmp/template.json

# 3. Modify the template for your new fault
# 4. Validate against schema before adding
```

# Reference Examples - Discover Dynamically

## Find Faults to Study

**Discover simple faults** (good starting points):
```bash
# Find short/simple fault files (likely easier to understand)
find scenarios/sre/roles/faults/tasks -name "inject_*.yaml" -exec wc -l {} \; | sort -n | head -10

# Search for specific patterns
ls scenarios/sre/roles/faults/tasks/inject_*image*.yaml
ls scenarios/sre/roles/faults/tasks/inject_*environment*.yaml
ls scenarios/sre/roles/faults/tasks/inject_*node*.yaml
```

**Discover complex faults** (advanced patterns):
```bash
# Find longer fault files (likely more complex)
find scenarios/sre/roles/faults/tasks -name "inject_*.yaml" -exec wc -l {} \; | sort -n | tail -10

# Search for multi-resource faults
grep -l "kubernetes.core.k8s:" scenarios/sre/roles/faults/tasks/inject_*.yaml | xargs grep -c "kubernetes.core.k8s:" | grep -v ":1$"

# Find Chaos Mesh integration
grep -l "chaos-mesh.org" scenarios/sre/roles/faults/tasks/inject_*.yaml

# Find node-level operations
grep -l "node\|cordon\|drain" scenarios/sre/roles/faults/tasks/inject_*.yaml
```

**Study faults by complexity:**
```bash
# Count steps in each fault to gauge complexity
for file in scenarios/sre/roles/faults/tasks/inject_*.yaml; do
  echo "$(grep -c "^- name:" "$file") steps: $(basename "$file")"
done | sort -n
```

# Anti-Patterns

❌ **Don't:**
- Skip brainstorming with available applications
- Guess service names without checking documentation
- Create faults without checking for similar existing ones
- Forget the `app.kubernetes.io/managed-by: ITBench` label
- Use hardcoded namespace/service names in fault index (use Jinja2 templates)

✅ **Do:**
- Start with incident description
- Map to available applications and their documentation
- Reference existing similar fault implementations
- Test in a real cluster before finalizing
- Follow consistent Ansible patterns
- Use Jinja2 templates in solutions for reusability

# Automatic Transition to Scenario Creation

**IMPORTANT**: After completing fault scaffolding, **automatically proceed** to scenario creation using the **scenario-scaffolding** skill.

**Do not wait for user prompt** - transition immediately to:
1. Apply this fault to the identified service/component
2. Populate scenario files with application, faults, and tools
3. Generate groundtruth.yaml with DSL format

This creates a complete end-to-end workflow: **Incident → Fault → Scenario → Ground Truth**
