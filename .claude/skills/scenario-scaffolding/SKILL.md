---
name: scenario-scaffolding
description: Assists with creating complete ITBench scenarios by applying fault mechanisms to specific services, populating scenario files, and generating groundtruth DSL with fault propagations and alert predictions.
---

# Purpose

This skill guides you through the complete scenario creation workflow:

1. **Fault Application** - Apply fault mechanism to a specific service/component
2. **Scenario File Population** - Define which application, faults, and tools
3. **Ground Truth Generation** - Create DSL with groups, propagations, and alerts

# When to Use This Skill

This skill auto-activates when:

- Working with files matching `**/scenarios/index.json`
- Editing files in `**/scenarios/files/scenario_*/`
- User mentions "scenario scaffold", "ground truth", "disruptions", "DSL"
- Creating or modifying scenario definitions

# Prerequisites

Before starting scenario scaffolding:
- ✅ Fault mechanism is **fully implemented** (Ansible task + fault index complete)
- ✅ You know the **target application** (OpenTelemetry Demo or BookInfo)
- ✅ You know the **specific service/component** to target

# Workflow

## Step 1: Apply Fault to Service/Component

**Dynamically identify available services for your chosen application:**

### 1.1 List Available Applications
```bash
# Extract all application keys from managers.yaml
grep -E "^  [a-z_]+:" scenarios/sre/roles/applications/defaults/main/managers.yaml | sed 's/://g' | awk '{print $1}'
```

### 1.2 Get Application Metadata
```bash
# Replace <app-key> with your chosen application
# Get namespace
grep -A 15 "^  <app-key>:" scenarios/sre/roles/applications/defaults/main/managers.yaml | grep "namespace:" | awk '{print $2}'

# Get documentation URL
grep -A 15 "^  <app-key>:" scenarios/sre/roles/applications/defaults/main/managers.yaml | grep -E "url:|documentation:"
```

### 1.3 Discover Services from Manifests
```bash
# Get the namespace from step 1.2
NAMESPACE="<namespace>"

# Find all Deployments in the application
grep -r "kind: Deployment" scenarios/sre/roles/applications/templates/kubernetes/ | grep "$NAMESPACE" | grep -oP 'name: \K[a-z0-9-]+'

# Find all Services
grep -r "kind: Service" scenarios/sre/roles/applications/templates/kubernetes/ | grep "$NAMESPACE" | grep -oP 'name: \K[a-z0-9-]+'

# Find all StatefulSets
grep -r "kind: StatefulSet" scenarios/sre/roles/applications/templates/kubernetes/ | grep "$NAMESPACE" | grep -oP 'name: \K[a-z0-9-]+'
```

### 1.4 Verify from Documentation
Consult the documentation URL from step 1.2 to understand:
- Service architecture
- Component roles
- Dependencies between services

**Select the service** that best demonstrates the fault mechanism.

## Step 2: Populate Scenario Files

The scenario consists of multiple files in `scenarios/sre/roles/scenarios/files/scenario_<ID>/`:

### 2.1 Scenario Index Entry

**File**: `scenarios/sre/roles/documentation/files/library/scenarios/index.json`

**Structure** (discovered dynamically):

First, get available tags and platforms:
```bash
# Get valid tags
jq '.properties.tags.items.enum' scenarios/sre/roles/documentation/files/library/faults/schema.json

# Get valid platforms
jq '.properties.platforms.items.enum' scenarios/sre/roles/documentation/files/library/faults/schema.json

# Get valid categories
jq '.properties.category.enum' scenarios/sre/roles/documentation/files/library/scenarios/schema.json
```

Then construct the scenario entry:
```json
{
  "id": <next-available-id>,
  "category": "<category-from-schema>",  // e.g., "sre", "finops", "ciso"
  "complexity": "<complexity>",  // "low", "medium", "high"
  "description": "User-facing incident description",
  "environment": {
    "applications": [
      {
        "id": "<application-id-from-step-1>"  // e.g., "opentelemetry-demo", "book-info"
      }
    ]
  },
  "platforms": ["<platform-from-schema>"],
  "tags": ["<tag1>", "<tag2>"],  // Match fault tags from schema

  // Populated in this step:
  "disruptions": [
    {
      "injections": [
        {
          "id": "<fault-id-from-faults-index>",
          "args": {
            // Arguments matching the fault's JSON schema
            "kubernetesObject": {
              "apiVersion": "apps/v1",
              "kind": "<kind>",
              "metadata": {
                "name": "<service-name-from-step-1>",
                "namespace": "<namespace-from-step-1>"
              }
            }
            // Additional args based on fault schema
          }
        }
      ],
      // Optional: post-injection hooks
      "waitFor": {
        "postInjection": [
          {
            "id": "restart-kubernetes-workload",
            "args": { /* restart args */ }
          }
        ]
      }
    }
  ],

  "alerts": [],  // Usually empty, unless specific alert requirements

  "solutions": [
    [
      {
        "steps": [
          {
            "text": "Step description",
            "command": "kubectl -n <namespace> <action> <kind>/<name>"
          }
        ]
      }
    ]
  ]
}
```

### 2.2 Understanding Disruptions

**Discover disruption patterns from existing scenarios:**
```bash
# Find scenarios using your chosen fault
FAULT_ID="<your-fault-id>"
jq --arg fault "$FAULT_ID" '.[] | select(.disruptions[].injections[].id == $fault) | {id, disruptions}' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json

# Examine a specific scenario's disruptions
SCENARIO_ID="<scenario-number>"
jq --arg id "$SCENARIO_ID" '.[] | select(.id == ($id | tonumber)) | .disruptions' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json
```

**Single Fault Injection** (template):
```json
{
  "disruptions": [
    {
      "injections": [
        {
          "id": "<fault-id>",
          "args": {
            "kubernetesObject": {
              "apiVersion": "apps/v1",
              "kind": "<Deployment|StatefulSet>",
              "metadata": {
                "name": "<service-name>",
                "namespace": "<namespace>"
              }
            },
            "container": {
              "name": "<container-name>"
            }
          }
        }
      ]
    }
  ]
}
```

**Multiple Fault Injections** (template):
```json
{
  "disruptions": [
    {
      "injections": [
        {
          "id": "<fault-id>",
          "args": {
            "kubernetesObject": {
              "apiVersion": "apps/v1",
              "kind": "Deployment",
              "metadata": {"name": "<service-1>", "namespace": "<namespace>"}
            }
          }
        },
        {
          "id": "<fault-id>",
          "args": {
            "kubernetesObject": {
              "apiVersion": "apps/v1",
              "kind": "Deployment",
              "metadata": {"name": "<service-2>", "namespace": "<namespace>"}
            }
          }
        }
      ]
    }
  ]
}
```

**With waitFor Hooks** (find examples dynamically):
```bash
# Find scenarios using waitFor patterns
jq '.[] | select(.disruptions[].waitFor != null) | {id, disruptions}' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json | head -50
```

### 2.3 waitFor Patterns

**When to use waitFor**:
- ConfigMap/Secret changes → Restart affected workloads
- Chaos Mesh experiments → Pause/delete schedules
- Multi-step setup → Wait for readiness

**Common waitFor IDs**:
- `restart-kubernetes-workload` - Restart a deployment
- `wait-kubernetes-workload-ready` - Wait for pod readiness

### 2.4 Solutions Format

**Discover solution patterns from the fault definition:**
```bash
# Get solutions from the fault entry
FAULT_ID="<your-fault-id>"
jq --arg fault "$FAULT_ID" '.[] | select(.id == $fault) | .solutions' \
  scenarios/sre/roles/documentation/files/library/faults/index.json
```

Adapt fault solutions to scenario context (replace Jinja2 templates with actual values):

**Single-step solution** (template):
```json
{
  "solutions": [
    [
      {
        "steps": [
          {
            "text": "Revert the last change done to the manifest.",
            "command": "kubectl -n <namespace> rollout undo <kind>/<name>"
          }
        ]
      }
    ],
    [
      {
        "steps": [
          {
            "text": "Manually edit the manifest and fix the issue.",
            "command": "kubectl -n <namespace> edit <kind> <name>"
          }
        ]
      }
    ]
  ]
}
```

**Multi-step solutions** (find examples):
```bash
# Find scenarios with multi-step solutions
jq '.[] | select(.solutions[][].steps | length > 1) | {id, solutions}' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json | head -100
```

### 2.5 Determine Required Tools

Based on disruptions, identify tools needed (captured by scaffolding from `scenarios/sre/roles/scaffolding/tasks/generate_new_scenario_files.yaml`):

**Chaos Mesh Detection**:
```yaml
enable_chaos_mesh: |-
  {{
    scaffolding_skeleton_scenario.disruptions |
    map(attribute="injections") |
    ansible.builtin.flatten |
    ansible.builtin.selectattr("id", "==", "scheduled-chaos-mesh-experiment") |
    ansible.builtin.length > 0
  }}
```

This is automatically determined when scenario files are generated.

## Step 3: Generate Ground Truth Files

Scenarios require **two ground truth files** in different formats:
1. **groundtruth.yaml** - v2 API (simplified entity-based format)
2. **groundtruth_v1.yaml** - v1 API (DSL format with groups and propagations)

### 3.0 Create groundtruth.yaml (v2 API)

**File**: `scenarios/sre/roles/scenarios/files/scenario_<ID>/groundtruth.yaml`

This is a **simplified format** that focuses on affected entities and solutions.

**Structure**:
```yaml
---
apiVersion: itbench.io/v2
kind: GroundTruth
metadata:
  name: scenario-<ID>
spec:
  # List of expected alerts
  alerts:
    - labels: {}
      name: <alert-name>  # e.g., KubePodNotReady, KubePodCrashLooping

  # List of affected Kubernetes resources (usually root cause)
  entities:
    - apiVersion: <api-version>
      kind: <kind>
      metadata:
        name: <resource-name>
        namespace: <namespace>

  # Solution paths (same as scenario index)
  solutions:
    - - steps:
          - command: <kubectl command>
            text: <step description>
```

**Example** (find real examples dynamically):
```bash
# View an existing groundtruth.yaml for reference
cat scenarios/sre/roles/scenarios/files/scenario_20/groundtruth.yaml

# Or examine multiple scenarios
ls scenarios/sre/roles/scenarios/files/scenario_*/groundtruth.yaml | head -5 | xargs -I {} sh -c 'echo "=== {} ===" && cat {}'
```

**Template**:
```yaml
---
apiVersion: itbench.io/v2
kind: GroundTruth
metadata:
  name: scenario-<ID>
spec:
  alerts:
    - labels: {}
      name: <alert-name>  # From fault's alerts.application
  entities:
    - apiVersion: apps/v1
      kind: <Deployment|StatefulSet|etc>
      metadata:
        name: <service-name>
        namespace: <namespace>
  solutions:
    - - steps:
          - command: kubectl -n <namespace> rollout undo <kind>/<name>
            text: Revert the last change done to the manifest.
      - steps:
          - command: kubectl -n <namespace> edit <kind> <name>
            text: Manually edit the manifest and fix the issue.
```

**Key Points**:
- **alerts**: List primary alerts that will fire (from fault index)
- **entities**: List the root cause resource(s) being modified by the fault
- **solutions**: Copy from scenario index (remove Jinja2 templates, use actual values)

### 3.1 Create groundtruth_v1.yaml (v1 API - DSL Format)

**File**: `scenarios/sre/roles/scenarios/files/scenario_<ID>/groundtruth_v1.yaml`

Ground truth uses **DSL format (groups)** to define fault propagation chains.

### 3.2 DSL Structure

```yaml
---
apiVersion: itbench.io/v1
kind: GroundTruth
metadata:
  name: scenario-<ID>
spec:
  # Predicted alerts
  alerts:
    - group_id: <group-id>
      id: <alert-name>
      metadata:
        description: <alert description>

  # Resource groups
  groups:
    - id: <unique-group-id>
      kind: <Pod|Service|Deployment|ConfigMap|etc>
      namespace: <namespace>
      name: <resource-name>  # OR filter: ["regex-pattern"]
      root_cause: true  # At least one group must be root cause

  # Logical relationships
  aliases:
    - [<group-id-1>, <group-id-2>, <group-id-3>]

  # Fault propagations
  propagations:
    - source: <group-id>
      target: <group-id>
      condition: <what causes propagation>
      effect: <what happens>

  # Optional: fault metadata
  fault:
    - category: Change  # or Create, Delete
      condition: <fault condition>
      entity:
        group_id: <group-id>
        kind: <kind>
        name: <name>
      fault_mechanism: <mechanism>

  # Recommended actions
  recommendedActions:
    - solution:
        actions:
          - <action description>
        id: <solution-id>
```

### 3.3 Defining Groups

**Groups** represent sets of Kubernetes resources.

**Required fields**:
- `id`: Unique identifier
- `kind`: Kubernetes kind (Pod, Service, Deployment, etc.)
- `namespace`: Kubernetes namespace
- One of:
  - `name`: Exact resource name, OR
  - `filter`: List of regex patterns

**Optional fields**:
- `root_cause`: boolean (at least one group must be `true`)

**Discover group patterns from existing scenarios:**
```bash
# View groups from a specific scenario
cat scenarios/sre/roles/scenarios/files/scenario_<ID>/groundtruth_v1.yaml | grep -A 10 "^  groups:"

# Find scenarios with ConfigMap root causes
grep -r "kind: ConfigMap" scenarios/sre/roles/scenarios/files/*/groundtruth_v1.yaml
```

**Pod group with filter** (template):
```yaml
groups:
  - id: <service-name>-pod-1
    kind: Pod
    namespace: <namespace>
    filter:
      - <service-name>-.*
    root_cause: true
```

**Service group with filter** (template):
```yaml
groups:
  - id: <service-name>-service-1
    kind: Service
    namespace: <namespace>
    filter:
      - <service-name>\b  # \b = word boundary
```

**ConfigMap group (root cause)** (template):
```yaml
groups:
  - id: <config-name>-cm
    kind: ConfigMap
    namespace: <namespace>
    name: <configmap-name>
    root_cause: true
```

### 3.4 Defining Aliases

**Aliases** link related groups logically.

```yaml
aliases:
  - [<group-id-1>, <group-id-2>, <group-id-3>]
```

**Discover alias patterns:**
```bash
# Find scenarios with aliases
grep -A 5 "^  aliases:" scenarios/sre/roles/scenarios/files/*/groundtruth_v1.yaml | head -20
```

**Template**:
```yaml
aliases:
  - - <service-name>-pod-1
    - <service-name>-service-1
  - - <dependent-service>-pod-1
    - <dependent-service>-service-1
```

### 3.5 Defining Propagations

**Propagations** describe how faults spread.

**Required fields**:
- `source`: Group ID where propagation starts
- `target`: Group ID where propagation ends
- `condition`: What causes the propagation
- `effect`: What observable impact results

**Discover propagation patterns:**
```bash
# Find propagation examples
grep -A 10 "^  propagations:" scenarios/sre/roles/scenarios/files/*/groundtruth_v1.yaml | head -50
```

**Template**:
```yaml
propagations:
  - source: <root-cause-group-id>
    target: <affected-service-group-id>
    condition: <what triggers propagation>
    effect: <observable impact>
  - source: <affected-service-group-id>
    target: <dependent-service-group-id>
    condition: <dependency relationship>
    effect: <downstream impact>
```

### 3.6 Predicting Alerts

**IMPORTANT**: Always read alert definitions from actual source files to get up-to-date alert rules.

**Alert Sources:**

1. **Application-Specific Alerts** - Read from local PrometheusRules:

   **OpenTelemetry Demo:**
   ```bash
   cat scenarios/sre/roles/applications/templates/kubernetes/otel_demo/prometheusrules.j2
   ```

   **BookInfo:**
   ```bash
   cat scenarios/sre/roles/applications/templates/kubernetes/book_info/prometheusrules.j2
   ```

2. **Kubernetes Platform Alerts** - Check:

   a. **Local schema** (available alerts in ITBench):
   ```bash
   jq '.properties.alerts.properties.application.items.enum' \
     scenarios/sre/roles/documentation/files/library/faults/schema.json
   ```

   b. **Prometheus Community Rules** (canonical source):
   - Reference: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack/templates/prometheus/rules-1.14
   - Search for alerts matching your fault symptoms (e.g., `KubePodCrashLooping`, `KubePodNotReady`)

**How to predict alerts:**
1. Read PrometheusRules files for the target application
2. Match fault symptoms to alert expressions
3. Identify which alerts will trigger based on fault behavior

**Alert format** (template):
```yaml
alerts:
  - group_id: <affected-service-group-id>
    id: <alert-name-from-prometheus-rules>
    metadata:
      description: <alert description matching PrometheusRules>
  - group_id: <affected-service-group-id>
    id: <another-alert-name>
    metadata:
      description: <another alert description>
```

### 3.7 Complete Example (groundtruth_v1.yaml)

**View real examples dynamically:**
```bash
# View a complete groundtruth_v1.yaml file
cat scenarios/sre/roles/scenarios/files/scenario_20/groundtruth_v1.yaml

# Compare multiple scenarios for patterns
for scenario in 20 30 40; do
  echo "=== Scenario $scenario ==="
  cat "scenarios/sre/roles/scenarios/files/scenario_${scenario}/groundtruth_v1.yaml" 2>/dev/null || echo "Not found"
  echo ""
done
```

**Complete Template:**
```yaml
---
apiVersion: itbench.io/v1
kind: GroundTruth
metadata:
  name: scenario-<ID>
spec:
  alerts:
    - group_id: <affected-service-group-id>
      id: <alert-name>
      metadata:
        description: <alert description from PrometheusRules>

  groups:
    - id: <root-cause-group-id>
      kind: <Pod|Deployment|ConfigMap>
      namespace: <namespace>
      filter:
        - <name-pattern-regex>
      root_cause: true

    - id: <affected-service-group-id>
      kind: Service
      namespace: <namespace>
      filter:
        - <service-name>\b

    - id: <dependent-service-group-id>
      kind: Service
      namespace: <namespace>
      filter:
        - <dependent-service-name>\b

  aliases:
    - - <root-cause-group-id>
      - <affected-service-group-id>

  propagations:
    - source: <root-cause-group-id>
      target: <affected-service-group-id>
      condition: <fault condition>
      effect: <direct impact>
    - source: <affected-service-group-id>
      target: <dependent-service-group-id>
      condition: <dependency relationship>
      effect: <downstream impact>

  fault:
    - category: <Change|Create|Delete>
      condition: <fault description>
      entity:
        group_id: <root-cause-group-id>
        kind: <kind>
        name: <name>
      fault_mechanism: <mechanism>

  recommendedActions:
    - solution:
        actions:
          - <action description>
        id: <solution-id>
    - solution:
        actions:
          - <alternative action>
        id: <alternative-solution-id>
```

# Validation & Generation

**IMPORTANT**: You must **manually create both groundtruth files** before running validation:

1. **Create groundtruth.yaml** (v2 API - simplified format)
2. **Create groundtruth_v1.yaml** (v1 API - DSL format)

After creating both files manually, validate with:

```bash
cd scenarios/sre
make regenerate-scenario-files
```

This validates and generates:
- `scenario_<ID>/scenario.yaml` - Scenario spec (auto-generated from index)

**Both groundtruth files must be created manually** - they are not auto-generated.

# Common Patterns

**Discover patterns dynamically by analyzing existing scenarios:**

## Identify Application-Specific Patterns

```bash
# Get all scenarios for a specific application
APP_ID="opentelemetry-demo"  # or "book-info"
jq --arg app "$APP_ID" '.[] | select(.environment.applications[].id == $app) | {id, description}' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json

# Analyze groundtruth patterns for that application
for scenario_id in $(jq --arg app "$APP_ID" '.[] | select(.environment.applications[].id == $app) | .id' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json); do
  echo "=== Scenario $scenario_id ==="
  cat "scenarios/sre/roles/scenarios/files/scenario_${scenario_id}/groundtruth_v1.yaml" | grep -E "^  (groups|propagations):" -A 20
done
```

## Common Propagation Patterns

**Find typical propagation chains:**
```bash
# Find Pod → Service propagations
grep -A 4 "source:.*pod" scenarios/sre/roles/scenarios/files/*/groundtruth_v1.yaml | grep "target:" | head -10

# Find Service → Service propagations
grep -A 4 "source:.*service" scenarios/sre/roles/scenarios/files/*/groundtruth_v1.yaml | grep "target:" | head -10
```

**Generic propagation chain template:**
```
<Root Cause Resource> (root_cause) → <Affected Service> → <Dependent Service> → Alerts
```

## ConfigMap Fault Patterns

**Discover ConfigMap scenarios:**
```bash
# Find scenarios with ConfigMap root causes
grep -r "kind: ConfigMap" scenarios/sre/roles/scenarios/files/*/groundtruth_v1.yaml -l | \
  xargs -I {} sh -c 'echo "=== {} ===" && cat {} | head -50'
```

**Template:**
```yaml
groups:
  - id: <config-name>-cm
    kind: ConfigMap
    namespace: <namespace>
    name: <configmap-name>
    root_cause: true

  - id: <affected-workload>-pod
    kind: Pod
    namespace: <namespace>
    filter: [<workload-name>-.*]

propagations:
  - source: <config-name>-cm
    target: <affected-workload>-pod
    condition: ConfigMap contains <type of issue>
    effect: <workload> pod <impact>
```

# Anti-Patterns

❌ **Don't:**
- Forget to set `root_cause: true` on at least one group
- Use duplicate group IDs
- Create propagations with undefined group IDs
- Skip alert prediction
- Use `entities` format (use `groups` instead)
- Leave `faultId` in final scenario (it's a scaffolding hint)

✅ **Do:**
- Mark the actual fault injection point as root cause
- Create groups for all affected resources
- Define propagations showing fault spread
- Predict alerts based on PrometheusRules
- Use regex filters for pod groups
- Test scenario generation with `make regenerate-scenario-files`
- Remove `faultId` after using it to build disruptions

# Reference Examples

**Discover reference scenarios dynamically by complexity:**

```bash
# Find simple scenarios (low complexity)
jq '.[] | select(.complexity == "low") | {id, description, faults: [.disruptions[].injections[].id]}' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json | head -50

# Find complex scenarios (high complexity)
jq '.[] | select(.complexity == "high") | {id, description, faults: [.disruptions[].injections[].id]}' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json | head -50

# Find scenarios using specific fault mechanisms
FAULT_ID="<your-fault-id>"
jq --arg fault "$FAULT_ID" '.[] | select(.disruptions[].injections[].id == $fault) | {id, description}' \
  scenarios/sre/roles/documentation/files/library/scenarios/index.json
```

**View groundtruth files for reference:**
```bash
# List all available groundtruth files
ls scenarios/sre/roles/scenarios/files/scenario_*/groundtruth_v1.yaml | sort -V

# View specific scenarios
cat scenarios/sre/roles/scenarios/files/scenario_1/groundtruth_v1.yaml   # Feature flag pattern
cat scenarios/sre/roles/scenarios/files/scenario_20/groundtruth_v1.yaml  # Image pull error
cat scenarios/sre/roles/scenarios/files/scenario_40/groundtruth_v1.yaml  # Code change pattern
```

# Tips

1. **Start with the fault mechanism** - What resource is being modified?
2. **Identify the root cause group** - The resource directly affected by the fault
3. **Map dependencies** - What services call the affected service?
4. **Predict observables** - What alerts will fire? What symptoms appear?
5. **Define propagation chain** - How does the fault spread through the system?
6. **Test generation** - Always run `make regenerate-scenario-files` to validate

# Next Steps

After scenario scaffolding:
1. Test the complete scenario in a development cluster
2. Verify alerts fire as predicted
3. Validate solutions actually work
4. Commit changes: `git add . && git commit -m "feat: add scenario <ID>"`
