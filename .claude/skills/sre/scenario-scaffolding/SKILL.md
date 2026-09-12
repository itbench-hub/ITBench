---
name: scenario-scaffolding
description: Assists with creating complete ITBench scenarios by applying fault mechanisms to specific services, populating scenario index templates, and generating groundtruth DSL with fault propagations and alert predictions.
---

# Purpose

This skill guides you through the complete scenario creation workflow:

1. **Fault Application** - Apply fault mechanism to a specific service/component
2. **Scenario Template Population** - Define which application, faults, and disruptions
3. **Ground Truth Generation** - Create DSL with groups, propagations, and alerts

# When to Use This Skill

This skill auto-activates when:

- Working with files matching `**/templates/library/indexes/scenarios/*.yaml.j2`
- Editing files in `**/library/specs/scenarios/*/`
- User mentions "scenario scaffold", "ground truth", "disruptions", "DSL"
- Creating or modifying scenario definitions

# Prerequisites

Before starting scenario scaffolding:
- ✅ Fault mechanism is **fully implemented** (Ansible task + fault index template complete)
- ✅ You know the **target application** (**prefer OpenTelemetry Demo** over BookInfo)
- ✅ You know the **specific service/component** to target

# Workflow

## Step 1: Apply Fault to Service/Component

### 1.1 Get application namespaces

```bash
cat scenarios/sre/project/roles/applications/vars/main/releases.yaml
```

This gives:
```yaml
applications_releases:
  book_info:
    name: book-info
    namespace: book-info
  opentelemetry_demo:
    name: otel-demo
    namespace: otel-demo
```

**Application Preference:**
- **Prefer OpenTelemetry Demo** (`opentelemetry_demo` / `otel-demo`) for most scenarios — it's richer, more comprehensive, and better maintained
- Use BookInfo (`book_info` / `book-info`) only if the fault specifically requires its simpler architecture

### 1.2 Discover Services from Manifests

```bash
NAMESPACE="otel-demo"  # or book-info

# Find all Deployments in the application
grep -r "kind: Deployment" scenarios/sre/project/roles/applications/templates/kubernetes/ | grep "$NAMESPACE"

# Find all Services
grep -r "kind: Service" scenarios/sre/project/roles/applications/templates/kubernetes/ | grep "$NAMESPACE"

# Find all StatefulSets
grep -r "kind: StatefulSet" scenarios/sre/project/roles/applications/templates/kubernetes/ | grep "$NAMESPACE"
```

### 1.2.1 Optional: Ground in Real Deployment

**Ask the user:**
> Would you like to deploy the application to a live cluster to get actual resource names? This requires a running Kubernetes cluster.

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
kubectl get configmaps -n otel-demo -o jsonpath='{.items[*].metadata.name}'
```

**If NO:** Continue with manifest-based discovery from Step 1.2

### 1.3 Verify from Documentation

Get documentation URLs from `library/indexes/applications/`:
```bash
jq '.resources' library/indexes/applications/2.json   # opentelemetry-demo
jq '.resources' library/indexes/applications/1.json   # book-info
```

Consult the documentation URL to understand:
- **Service architecture diagram** — shows how services connect and depend on each other
- Component roles and dependencies

**IMPORTANT**: Study the architecture diagram carefully — it's essential for understanding service dependencies and predicting which alerts will fire.

**Select the service** that best demonstrates the fault mechanism.

## Step 2: Scaffold the Scenario

Run from the **root directory**:

```bash
make scaffold-scenario
```

This prompts for a description and writes a new `templates/library/indexes/scenarios/<N>.yaml.j2` stub with empty fields.

## Step 3: Populate the Scenario Index Template

**File**: `templates/library/indexes/scenarios/<N>.yaml.j2`

### 3.1 Get the application ID

Application IDs come from `library/indexes/applications/`:
```bash
jq '.id' library/indexes/applications/1.json   # "book-info"
jq '.id' library/indexes/applications/2.json   # "opentelemetry-demo"
```

Get valid categories and complexity values from the scenario schema:
```bash
jq '.properties.category.enum' schemas/json/library/index/scenario.json
jq '.properties.complexity.enum' schemas/json/library/index/scenario.json
```

### 3.2 Build the disruptions block

Discover which fault index number corresponds to your fault:
```bash
grep -rl '"id": "<fault-id>"' library/indexes/faults/
```

**Discover disruption patterns from existing scenario templates:**
```bash
# Find scenarios using your chosen fault
grep -rl '"<fault-id>"' templates/library/indexes/scenarios/

# View a specific scenario template
cat templates/library/indexes/scenarios/20.yaml.j2
```

**Single Fault Injection** (template):
```yaml
disruptions:
  - injections:
      - id: <fault-id>
        args:
          kubernetesObject:
            apiVersion: apps/v1
            kind: <Deployment|StatefulSet>
            metadata:
              name: <service-name>
              namespace: <namespace>
          # Additional args based on fault schema
```

**With waitFor Hooks** — use when ConfigMap/Secret changes require a workload restart:
```yaml
disruptions:
  - injections:
      - id: <fault-id>
        args:
          kubernetesObject:
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: <configmap-name>
              namespace: <namespace>
    waitFor:
      postInjection:
        - id: restart-kubernetes-workload
          args:
            kubernetesObject:
              apiVersion: apps/v1
              kind: Deployment
              metadata:
                name: <deployment-name>
                namespace: <namespace>
```

**Find existing waitFor examples:**
```bash
grep -rl "waitFor" templates/library/indexes/scenarios/
```

### 3.3 Build the solutions block

Get solutions from the fault's rendered index entry:
```bash
FAULT_NUM=<N>
jq '.solutions' library/indexes/faults/${FAULT_NUM}.json
```

Adapt fault solution templates to scenario context (replace Jinja2 `{{ args.* }}` with actual values):

```yaml
solutionTemplates:
  - - steps:
        - text: Revert the last change done to the manifest.
          command: kubectl -n <namespace> rollout undo <kind>/<name>
  - - steps:
        - text: Manually edit the manifest and fix the issue.
          command: kubectl -n <namespace> edit <kind> <name>
```

### 3.4 Determine Required Tools

Chaos Mesh is enabled automatically when the `scheduled-chaos-mesh-experiment` fault is used. No manual configuration needed — it's detected from the disruptions list when running `make generate-resource-files`.

## Step 4: Generate Ground Truth Files

Scenarios require **two ground truth files** in `library/specs/scenarios/<ID>/`:

1. **groundtruth.yaml** — v2 API (simplified entity-based format)
2. **groundtruth_v1.yaml** — v1 API (DSL format with groups and propagations)

These files live in `library/specs/scenarios/<ID>/` and must be created **manually** — they are not auto-generated.

### 4.1 Create groundtruth.yaml (v2 API)

**File**: `library/specs/scenarios/<ID>/groundtruth.yaml`

**View existing examples:**
```bash
cat library/specs/scenarios/20/groundtruth.yaml
ls library/specs/scenarios/*/groundtruth.yaml | head -5 | xargs -I {} sh -c 'echo "=== {} ===" && cat {}'
```

**Template:**
```yaml
---
apiVersion: itbench.io/v2
kind: GroundTruth
metadata:
  name: scenario-<ID>
spec:
  alerts:
    - labels: {}
      name: <alert-name>  # e.g., KubePodNotReady, KubePodCrashLooping

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

**Key Points:**
- **alerts**: Primary alerts that will fire (from fault's `alerts.application`)
- **entities**: The root cause resource(s) being modified by the fault
- **solutions**: Actual values, no Jinja2 templates

### 4.2 Create groundtruth_v1.yaml (v1 API — DSL Format)

**File**: `library/specs/scenarios/<ID>/groundtruth_v1.yaml`

**View existing examples:**
```bash
cat library/specs/scenarios/20/groundtruth_v1.yaml
cat library/specs/scenarios/1/groundtruth_v1.yaml    # Feature flag pattern
cat library/specs/scenarios/40/groundtruth_v1.yaml   # Code change pattern
```

### 4.3 DSL Structure

```yaml
---
apiVersion: itbench.io/v1
kind: GroundTruth
metadata:
  name: scenario-<ID>
spec:
  alerts:
    - group_id: <group-id>
      id: <alert-name>
      metadata:
        description: <alert description>

  groups:
    - id: <unique-group-id>
      kind: <Pod|Service|Deployment|ConfigMap|etc>
      namespace: <namespace>
      name: <resource-name>        # OR use filter below
      filter: ["<regex-pattern>"]  # use for Pods (dynamic names)
      root_cause: true             # at least one group must be true

  aliases:
    - [<group-id-1>, <group-id-2>]

  propagations:
    - source: <group-id>
      target: <group-id>
      condition: <what causes propagation>
      effect: <what happens>

  fault:
    - category: Change  # or Create, Delete
      condition: <fault condition>
      entity:
        group_id: <group-id>
        kind: <kind>
        name: <name>
      fault_mechanism: <mechanism>

  recommendedActions:
    - solution:
        actions:
          - <action description>
        id: <solution-id>
```

### 4.4 Defining Groups

**Required fields**: `id`, `kind`, `namespace`, and one of `name` or `filter`

**Pod group with filter** (use for Pods — names include random suffixes):
```yaml
- id: <service-name>-pod-1
  kind: Pod
  namespace: <namespace>
  filter:
    - <service-name>-.*
  root_cause: true
```

**Service group:**
```yaml
- id: <service-name>-service-1
  kind: Service
  namespace: <namespace>
  filter:
    - <service-name>\b
```

**ConfigMap group (root cause):**
```yaml
- id: <config-name>-cm
  kind: ConfigMap
  namespace: <namespace>
  name: <configmap-name>
  root_cause: true
```

**Discover group patterns from existing scenarios:**
```bash
grep -r "root_cause: true" library/specs/scenarios/*/groundtruth_v1.yaml -l
grep -A 6 "root_cause: true" library/specs/scenarios/20/groundtruth_v1.yaml
```

### 4.5 Defining Propagations

**IMPORTANT**: Use the **architecture diagram** from the application's documentation to map the propagation path.

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

**Discover patterns:**
```bash
grep -A 6 "^  propagations:" library/specs/scenarios/*/groundtruth_v1.yaml | head -50
```

### 4.6 Predicting Alerts

**Read alert definitions from actual source files:**

1. **Application-Specific Alerts:**
   ```bash
   cat scenarios/sre/project/roles/applications/templates/kubernetes/otel_demo/prometheusrules.j2
   cat scenarios/sre/project/roles/applications/templates/kubernetes/book_info/prometheusrules.j2
   ```

2. **Available alert names from schema:**
   ```bash
   jq '.properties.alerts.properties.application.items.enum' schemas/json/library/index/fault.json
   ```

3. **Kubernetes platform alerts** — Reference: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack/templates/prometheus/rules-1.14

**How to predict alerts:**
1. Read PrometheusRules for the target application
2. Match fault symptoms to alert expressions
3. Identify which alerts will trigger based on fault behavior and architecture diagram

## Step 5: Validate and Generate

After creating both groundtruth files, run from the **root directory**:

```bash
make generate-library    # generates documentation and scenario.yaml spec
make validate-library    # validates all indexes against schemas
```

Then from `scenarios/sre/`:

```bash
make generate-resource-files   # generates Ansible role files
```

This produces `library/specs/scenarios/<ID>/scenario.yaml` (auto-generated from the index template).

# Common Patterns

## Discover Application-Specific Patterns

```bash
# Get all scenario templates for a specific application
grep -rl '"opentelemetry-demo"' templates/library/indexes/scenarios/

# View groundtruth patterns for a few scenarios
for id in 20 30 40; do
  echo "=== Scenario $id ==="
  cat "library/specs/scenarios/${id}/groundtruth_v1.yaml" 2>/dev/null | grep -E "^  (groups|propagations):" -A 20
done
```

## ConfigMap Fault Pattern

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

**Find ConfigMap scenarios:**
```bash
grep -rl "kind: ConfigMap" library/specs/scenarios/*/groundtruth_v1.yaml
```

# Anti-Patterns

❌ **Don't:**
- Forget to set `root_cause: true` on at least one group
- Use duplicate group IDs
- Create propagations with undefined group IDs
- Skip alert prediction
- Leave Jinja2 template variables in groundtruth files (use actual values)
- **Use obvious fault-revealing names for injected resources** (e.g., `malformed-config`, `fault-injector`)

✅ **Do:**
- Mark the actual fault injection point as root cause
- Create groups for all affected resources
- Define propagations showing fault spread
- Predict alerts based on PrometheusRules and architecture diagram
- Use regex filters for Pod groups (dynamic names)
- Run `make generate-library` to validate
- **Use non-obvious names for injected resources** (e.g., `app-config`, `recommendation-features`, `cache-helper`)

# Reference Examples

```bash
# Find simple scenarios (low complexity)
grep -rl '"complexity": "low"' library/indexes/scenarios/ | head -5

# Find complex scenarios (high complexity)
grep -rl '"complexity": "high"' library/indexes/scenarios/ | head -5

# List all groundtruth files
ls library/specs/scenarios/*/groundtruth_v1.yaml | sort -V

# View specific reference scenarios
cat library/specs/scenarios/1/groundtruth_v1.yaml    # Feature flag pattern
cat library/specs/scenarios/20/groundtruth_v1.yaml   # Image pull error
cat library/specs/scenarios/40/groundtruth_v1.yaml   # Code change pattern
```

# Tips

1. **Start with the architecture diagram** — review the application's architecture from its documentation URL (`library/indexes/applications/2.json`)
2. **Identify the fault mechanism** — what resource is being modified?
3. **Identify the root cause group** — the resource directly affected by the fault
4. **Map dependencies using the diagram** — which services call the affected service?
5. **Predict observables** — which services will be impacted and what alerts will fire?
6. **Define propagation chain** — root cause → dependencies → downstream effects
7. **Test generation** — always run `make generate-library` to validate

# Next Steps

After scenario scaffolding:
1. Test the complete scenario in a development cluster
2. Verify alerts fire as predicted
3. Validate solutions actually work
4. Commit changes: `git add . && git commit -m "feat: add scenario <ID>"`
