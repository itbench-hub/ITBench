# Multi-Vendor Observability Support (Layer A)

Design and implementation plan for deploying third-party SaaS observability
agents into ITBench SRE clusters, for both local and AWX-driven deployments.

Vendors in scope: **Datadog, Dynatrace**.

- **Layer A (this document):** deploy each vendor's agent/collector into the
  Kubernetes/OpenShift cluster so telemetry flows to the vendor's SaaS tenant.
- **Layer B (future):** expose each vendor's tenant URL + a scoped read token to
  the diagnosing SRE agent via the agent bundle so it can query telemetry during
  incidents. Out of scope here.

All backends are **SaaS**. This is the key architectural difference from the
existing in-cluster tools (Prometheus, ClickHouse, Jaeger), whose endpoints and
credentials are *discovered at runtime* from cluster Services/Secrets. SaaS
vendors invert this: **credentials are inputs** supplied by the operator, and
there is **no in-cluster endpoint to discover** — the "endpoint" is the vendor's
tenant URL.

---

## Existing conventions (how tools are wired today)

The SRE tooling lives under `scenarios/sre/`. There is no OO interface; it is an
Ansible convention-over-configuration pattern:

| Concern | Mechanism |
|---------|-----------|
| Tool registry | `tools_managers` dict in `project/roles/tools/defaults/main/managers.yaml` |
| Install/uninstall "interface" | Task-file naming: `install_<x>.yaml`, `uninstall_<x>.yaml` |
| Endpoint discovery | `set_internal_endpoints_<x>.yaml` / `set_external_endpoints_<x>.yaml` |
| Credentials | `set_credentials_<x>.yaml` (reads K8s Secrets) |
| Orchestration | `project/roles/tools/tasks/install.yaml` imports each installer, flag-gated |
| Enablement | Boolean flags in `group_vars` mapped via `project/manage_tools.yaml` |
| Helm values | `templates/helm/<tool>/values.j2` |
| K8s resources | `templates/kubernetes/<tool>/<resource>.j2` |
| AWX | `project/roles/awx/` job templates + custom credential types |

Reference install to copy for Helm-based tools: `install_opencost.yaml`.

---

## Status summary

- **Dynatrace: implemented and validated on OpenShift (CRC).** Full lifecycle
  exercised against a live OpenShift cluster + real Dynatrace tenant: operator
  install (chart `1.9.0`, `platform=openshift`), multi-DynaKube manifest
  (`v1beta6`) validation, namespace ownership, collision check, apply, DynaKube
  reconcile, and staged credential-independent uninstall with namespace
  preservation. Validation surfaced and fixed four issues: relative manifest path
  resolution, the collision-check helper's `no_log` interaction, uninstall
  discovering the DynaKube API version from the CRD, and allowing multiple
  DynaKube documents. Not yet validated on plain (non-OpenShift) Kubernetes.
- **Datadog: implemented, unvalidated.** All install/uninstall/AWX/validation
  code exists and passes YAML/schema checks, but has **not** been run against a
  live cluster or SaaS tenant, and remains blocked on OpenShift.

Molecule coverage is **required** before a vendor is treated as validated:
- `molecule/vendor_contract/` — credential-free, cluster-free contract tests
  (manifest validation, Secret-document rejection, secret/key-reference
  matching, and the non-secret projection allowlist). Always runs.
- `molecule/deployment_vendors/` — opt-in live deploy that self-skips when vendor
  secrets are absent.

### OpenShift support

**Dynatrace: supported and validated on OpenShift** (CRC / OpenShift, cluster
`1.35.5`, operator chart `1.9.0`). The `dynatrace-operator` Helm chart natively
handles OpenShift: setting `platform=openshift` makes the operator create and
manage the `SecurityContextConstraints` its agents (OneAgent, ActiveGate, CSI
driver) need. We therefore do **not** hand-craft SCCs for Dynatrace — the
install task sets the `platform` Helm value on OpenShift and the operator owns
its SCCs (Helm uninstall removes them). Validated end-to-end: operator + webhook
+ CSI driver + ActiveGate + OTel collector reached Running; DynaKube resources
reconciled; uninstall staged cleanly (DynaKube → operator → workload drain) and
preserved the namespace when not exclusively ITBench-owned.

##### KSPM AppArmor host path on RHEL CoreOS (edit your `dynakube.yaml`)

If the DynaKube enables **KSPM** (Kubernetes Security Posture Management), the
operator generates a `node-config-collector` DaemonSet that mounts every
`spec.kspm.mappedHostPaths` entry as a `hostPath` with `type: Directory`. The
onboarding UI commonly includes `/sys/kernel/security/apparmor` in that list.

RHEL CoreOS — the OpenShift node OS — uses **SELinux, not AppArmor**, so
`/sys/kernel/security/apparmor` does not exist on the node. The mount then fails
with `hostPath type check failed: /sys/kernel/security/apparmor is not a
directory` and the collector pod is stuck in `ContainerCreating`.

Because ITBench treats the downloaded `dynakube.yaml` as authoritative and does
**not** rewrite its spec, the fix is made in **your file**: remove that one entry
from `spec.kspm.mappedHostPaths`. KSPM otherwise stays fully enabled.

```yaml
  kspm:
    mappedHostPaths:
      - /boot
      - /etc
      - /proc/sys/kernel
      - /sys/fs
      # - /sys/kernel/security/apparmor   # remove on SELinux nodes (RHEL CoreOS)
      - /usr/lib/systemd/system
      - /var/lib
```

Re-run the tools playbook after editing; the operator regenerates the DaemonSet
without the AppArmor mount and the collector reaches `Running`. This caveat is
also documented inline at the top of
`project/roles/tools/tasks/install_dynatrace.yaml`.

**Datadog: still blocked on OpenShift** (hard assertion). The Datadog operator's
OpenShift SCC story has not been validated here; the block stays until it is.

> Note: Some older subsections below still describe an earlier namespace-`.j2` /
> SCC-annotation approach and an `allow_openshift` override. Those are superseded:
> namespaces are created via `ensure_vendor_namespace.yaml`, and Dynatrace
> OpenShift support is via the chart's `platform=openshift` value (not custom
> SCCs).

#### Future work: how to unblock OpenShift (decision: implement later)

The repo already has a working SCC precedent, so the intended path is settled —
it is deferred only until an OpenShift cluster + vendor tenant is available to
validate the specifics. **Chosen approach: custom least-privilege SCCs bound to
the agent service accounts (the Chaos Mesh pattern in
`install_chaos_mesh.yaml:6-57` / `uninstall_chaos_mesh.yaml:40-67`).** This was
preferred over binding to the built-in `system:openshift:scc:privileged`
(the `RoleBinding` idiom in `applications/.../install_opentelemetry_demo.yaml:52-69`)
because `privileged` grants far more than these agents need; the benchmark runs
untrusted workloads alongside fault injection, so least privilege matters.

To implement (per vendor), inside a `when: tools_cluster.platform == 'openshift'`
block, mirroring Chaos Mesh:
1. Create a `SecurityContextConstraints` labeled
   `app.kubernetes.io/managed-by: ITBench` + a per-vendor component label,
   enumerating ONLY the capabilities/volumes the agents require (do not blanket
   `allowPrivilegedContainer` unless proven necessary).
2. Bind it via the SCC `users:` list to the exact ServiceAccounts the operator
   creates. These names are **UNVERIFIED** and must be confirmed against the
   installed operator version, e.g. (indicative, verify before use):
   - Datadog: `<DatadogAgent name>-agent`, `<name>-cluster-agent`, plus the
     operator SA `datadog-operator`.
   - Dynatrace: OneAgent, ActiveGate, CSI driver, webhook, and operator SAs
     under the `dynatrace` namespace.
3. Remove the OpenShift-blocking assertion in the installers and add labeled SCC
   cleanup to the uninstallers (query by the ITBench labels, delete — as
   `uninstall_chaos_mesh.yaml` does).
4. Validate on a real OpenShift cluster: agents reach Ready, no
   `CreateContainerError`/SCC-denied events, and uninstall removes the SCCs.

Until steps 1-4 are done and validated, OpenShift stays hard-blocked.

## Cross-cutting design decisions

1. **New registry section.** SaaS vendors get a parallel `tools_vendors` dict in
   `project/roles/tools/defaults/main/vendors.yaml` (rather than overloading
   `tools_managers`), since they carry SaaS-specific attributes.
2. **Non-secret config** (site, region, tenant URL, enable flags) lives in
   `inventory/group_vars/environment/observability_vendors.yaml(.example)`.
3. **Secrets are inputs, source-agnostic.** Credential tasks read from a variable
   with an env fallback so the same task works locally and under AWX:
   `{{ datadog_api_key | default(lookup('ansible.builtin.env','DATADOG_API_KEY'), true) }}`.
   All secret-handling tasks use `no_log: true`. Secrets are never committed.
4. **Enablement** via per-vendor booleans mapped through `manage_tools.yaml` into
   `tools_configuration.vendors.<name>.enabled`, gating each install.
4a. **Single role-input interface.** The tools role reads vendor config **only**
   from `tools_configuration.vendors.*` (never from the global
   `observability_vendors` directly), so AWX and role tests have one contract.
4b. **Vendor installs run outside the SRE/FinOps gate** so a vendor-only
   deployment works.
4c. **Uninstall is unconditional, idempotent, credential-independent, and
   ownership-scoped.** It runs during Undeploy-Tools regardless of the enabled
   flag (so disabling a vendor still removes it), no-ops when the namespace is
   absent, only deletes resources labeled `itbench.io/observability-vendor=<v>`,
   and only deletes the namespace when it is ITBench-owned and drained. No blind
   `delete_all` of all CRs or unconditional namespace deletion.
4d. **Manifests are treated as untrusted + secret.** User CR files are validated
   (allowed kinds/apiVersions, exactly one primary CR, namespace pinning, doc
   count, null-doc rejection) before apply, and all parse/apply steps use
   `no_log: true`.
4e. **CRD retention.** Helm typically leaves chart CRDs behind on uninstall; we
   preserve them by default (do not force-delete vendor CRDs) to avoid breaking
   any remaining vendor CRs cluster-wide.
5. **AWX trigger** reuses the existing `Deploy-Tools`/`Undeploy-Tools` job
   templates (vendor installs run inside `manage_tools.yaml`, flag-gated). No new
   job templates.
6. **AWX secret delivery** uses custom AWX **credential types** (precedent: the
   `Kubeconfig` credential type in `configure_credentials.yaml`), injecting
   secrets as `extra_vars` (or files) into the Deploy-Tools job pod.
6a. **AWX input plumbing.** `manage_awx.yaml` combines a `vendors` group_var into
   `awx_configuration.vendors` (with `no_log`). Non-secret vendor config reaches
   the Deploy/Undeploy-Tools job templates via `extra_vars`
   (`observability_vendors`), built by a projection in `configure_jobs.yaml` that
   **strips secret keys** (`manifest`, `dynakube`, `api_key`, `app_key`). Secrets
   reach the job only through the injected vendor credential.
6b. **Vendor credentials are scoped to the tools nodes only.** A separate
   `node_tools_credentials` list (template `node_tools_credentials.j2`) carries
   the vendor credentials and is attached only to the `node-deploy-tools` /
   `node-undeploy-tools` workflow nodes. All other nodes keep the vendor-free
   `node_credentials` list, so fault-injection and Run-Agent jobs never receive
   vendor secrets.
6c. **AWX role argument spec is generated.** `meta/argument_specs.yaml` is
   rendered from `templates/meta/argument_specs.j2`; vendor specs live in the
   template (the generated file is overwritten on regeneration).
6d. **Plaintext-to-AWX path.** The `vendors` group_var
   (`inventory/group_vars/runner/vendors.yaml.example`) holds the secret inputs
   and must be Ansible-Vault encrypted or sourced from a secret manager. AWX
   stores the resulting credentials encrypted; provisioning tasks use `no_log`.

### Secret handling under AWX — why not plain env vars

AWX runs playbooks in ephemeral job pods (the `ITBench-Custom-EE` execution
environment). There is no shell where an operator `export`ed variables, and job
pods don't inherit host env vars, so `lookup('env', ...)` returns empty. AWX
credential types inject values into the job pod at runtime (as env/extra_vars or
files) and store them encrypted at rest. The source-agnostic variable form above
picks these up transparently.

Precedent: the `Kubeconfig` custom credential type
(`project/roles/awx/tasks/configure_credentials.yaml`, and injectors JSON at
`project/roles/awx/files/awx/credential_types/kubeconfig_injectors.json`)
supports both `extra_vars` and `file` injection.

> **Note (pre-existing security debt):** plaintext secrets are currently committed
> in `group_vars/runner/agent.yaml` (watsonx api_key, GitHub PAT) and
> `group_vars/runner/credentials.yaml` (AWS keys). These should be rotated and
> removed; this work deliberately avoids adding new plaintext secrets.

---

## Per-vendor deploy summary

| Vendor | Helm chart | CR applied | Required secrets |
|--------|-----------|-----------|------------------|
| Datadog | `datadog-operator` (helm.datadoghq.com) | `DatadogAgent` (from user's file) | `DATADOG_API_KEY` (+ `DATADOG_APP_KEY` when the CR references `appSecret`) |
| Dynatrace | `dynatrace-operator` (OCI) | `DynaKube` (from user's file) | tokens embedded in downloaded `dynakube.yaml` |

Common concerns: OpenShift SCC for privileged agents (precedent
`install_chaos_mesh.yaml`), Istio ambient (ztunnel) coexistence, kind
limitations for eBPF/full-stack agents, and pinned chart versions with renovate
annotations.

---

## Implementation status

| Item | File | Status |
|------|------|--------|
| Vendor registry | `project/roles/tools/defaults/main/vendors.yaml` | Created |
| Non-secret config (+ example) | `inventory/group_vars/environment/observability_vendors.yaml(.example)` | Created |
| `.gitignore` for `secrets/` | `scenarios/sre/.gitignore` | Created |
| Datadog creds | `project/roles/tools/tasks/set_credentials_datadog.yaml` | **Done** (source-agnostic) |
| Datadog namespace | `templates/kubernetes/datadog/namespace.j2` | **Done** |
| Datadog install/uninstall | `tasks/install_datadog.yaml`, `uninstall_datadog.yaml` | **Done** |
| Datadog orchestration wiring | `tasks/install.yaml`, `uninstall.yaml`, `manage_tools.yaml` | **Done** |
| Datadog AWX credential/wiring | `project/roles/awx/*` | **Done** |
| Dynatrace install/uninstall/AWX | `tasks/install_dynatrace.yaml`, `uninstall_dynatrace.yaml`, `awx/*` | **Implemented, unvalidated** (consumes user's `dynakube.yaml`; namespace created via `ensure_vendor_namespace.yaml`; `set_credentials_dynatrace.yaml` removed) |
| Shared ownership helpers | `tasks/ensure_vendor_namespace.yaml`, `assert_vendor_resource_ownership.yaml`, `delete_vendor_namespace_if_safe.yaml` | **Done** |
| Datadog manifest validation | `tasks/validate_datadog_manifest.yaml` | **Done** |
| Molecule: live deploy (opt-in) | `molecule/deployment_vendors/` | **Done** (self-skips without vendor secrets) |
| Molecule: credential-free contract | `molecule/vendor_contract/` | **Done** (validation, secret rejection, projection allowlist) |

---

## Dynatrace (implemented) — detailed plan

> Status: built. Registry pinned to operator `1.9.0` (OCI
> `oci://public.ecr.aws/dynatrace/dynatrace-operator`), install/uninstall/namespace
> tasks created, wired into `install.yaml`/`uninstall.yaml` (flag-gated on
> `tools_configuration.vendors.dynatrace.enabled`), AWX `Dynatrace` file-injector
> credential added, and the superseded `set_credentials_dynatrace.yaml` removed.


Dynatrace's onboarding UI produces a self-contained `dynakube.yaml` (a `Secret`
with `apiToken` + `dataIngestToken`, plus a `DynaKube` CR carrying apiUrl,
cluster name, and config). We **consume that file as-is** rather than
reconstruct it.

### Decisions

- Consume the downloaded `dynakube.yaml` unchanged (apply Secret + DynaKube after
  the operator is installed).
- A single variable `dynatrace_dynakube_path` drives both local and AWX paths, so
  `install_dynatrace.yaml` is identical in both contexts.
- **Local:** user places file at `secrets/dynatrace/dynakube.yaml` (gitignored);
  path configurable via `observability_vendors.dynatrace.dynakube_path`.
- **AWX:** custom `Dynatrace-Dynakube` credential type with a **file injector**
  (Kubeconfig precedent); user pastes file contents once, AWX materializes it as
  a file in the job pod and sets `dynatrace_dynakube_path` to `tower.filename.dynakube`.
- **Helm:** OCI chart `oci://public.ecr.aws/dynatrace/dynatrace-operator`, pinned
  `chart_version: 1.9.0`, `create_namespace: true`, `atomic: true` (v3 form).
- Reuse `Deploy-Tools`/`Undeploy-Tools`; flag-gated by
  `tools_configuration.vendors.dynatrace.enabled`.

Because the file carries everything, Dynatrace needs **no** `set_credentials`,
**no** `values.j2`, and **no** `dynakube.j2`. (An OpenShift-only `namespace.j2`
for SCC annotations is still needed.)

### Files

1. **`defaults/main/vendors.yaml`** (modify dynatrace entry):
   ```yaml
   dynatrace:
     helm:
       chart:
         # renovate: datasource=docker depName=public.ecr.aws/dynatrace/dynatrace-operator
         reference: oci://public.ecr.aws/dynatrace/dynatrace-operator
         version: 1.9.0
       release:
         name: dynatrace-operator
     kubernetes:
       namespace: dynatrace
   ```

2. **`inventory/group_vars/environment/observability_vendors.yaml(.example)`**
   (modify dynatrace block):
   ```yaml
   dynatrace:
     enabled: false
     # Path to dynakube.yaml downloaded from the Dynatrace onboarding UI
     # (contains the Secret with tokens + the DynaKube CR). Keep OUT of git.
     dynakube_path: "secrets/dynatrace/dynakube.yaml"
   ```

3. **`scenarios/sre/.gitignore`** (create): add `secrets/`.

4. **`tasks/install_dynatrace.yaml`** (create):
   1. Resolve `dynatrace_dynakube_path` = `tower.filename.dynakube` if defined
      (AWX) else `observability_vendors.dynatrace.dynakube_path`.
   2. `stat` + assert file exists / non-empty (`no_log: true`).
   3. OpenShift only: create `dynatrace` ns from
      `templates/kubernetes/dynatrace/namespace.j2` (SCC annotations) before install.
   4. Helm install:
      ```yaml
      kubernetes.core.helm:
        chart_ref: "{{ tools_vendors.dynatrace.helm.chart.reference }}"
        chart_version: "{{ tools_vendors.dynatrace.helm.chart.version }}"
        kubeconfig: "{{ tools_cluster.kubeconfig }}"
        release_name: "{{ tools_vendors.dynatrace.helm.release.name }}"
        release_namespace: "{{ tools_vendors.dynatrace.kubernetes.namespace }}"
        release_state: present
        create_namespace: true
        atomic: true
        wait: true
      ```
   5. Wait for the operator webhook Deployment to be Available (retry/until) —
      DynaKube apply fails if the webhook isn't up yet.
   6. Apply the user's file:
      ```yaml
      kubernetes.core.k8s:
        kubeconfig: "{{ tools_cluster.kubeconfig }}"
        definition: "{{ lookup('ansible.builtin.file', dynatrace_dynakube_path) | ansible.builtin.from_yaml_all | list }}"
        state: present
        wait: true
      # no_log: true
      ```

5. **`tasks/uninstall_dynatrace.yaml`** (create): delete DynaKube CR + its Secret
   (by file if present, else by name/label), helm `release_state: absent`, delete
   namespace — all `wait: true`, guarded to no-op if file absent.

6. **`templates/kubernetes/dynatrace/namespace.j2`** (create — OpenShift SCC only):
   standard ITBench namespace with `{% if tools_cluster.platform == 'openshift' %}`
   scc annotations.

7. **Orchestration wiring** (modify):
   - `tasks/install.yaml`: flag-gated import of `install_dynatrace.yaml`
     (`when: tools_configuration.vendors.dynatrace.enabled | default(false)`).
   - `tasks/uninstall.yaml`: matching reverse-order import.
   - `manage_tools.yaml`: add `vendors: "{{ observability_vendors | default({}) }}"`
     to `tools_configuration` (both the scenario_id and non-scenario branches);
     pass `observability_vendors` into the tools role vars.

8. **AWX credential** (file injector — Kubeconfig precedent):
   - Create `project/roles/awx/files/awx/credential_types/dynatrace_dynakube_injectors.json`:
     ```json
     {
       "extra_vars": { "dynatrace_dynakube_path": "{{ tower.filename.dynakube }}" },
       "file": { "template.dynakube": "{{ dynakube }}" }
     }
     ```
   - Modify `project/roles/awx/tasks/configure_credentials.yaml`: create a
     `Dynatrace-Dynakube` credential type (one multiline `secret: true` field <!-- pragma: allowlist secret -->
     `dynakube`, injectors from the JSON) + a credential instance whose
     `inputs.dynakube` is sourced from `awx_configuration.vendors.dynatrace.dynakube`.
     Gate on Dynatrace enabled.
   - Modify `project/roles/awx/templates/awx/workflows/node_credentials.j2`: add
     `- name: Dynatrace-Dynakube` when enabled.
   - Modify `project/roles/awx/meta/argument_specs.yaml`: document
     `awx_configuration.vendors.dynatrace.dynakube`.

9. **Docs**: `.example` comments explain (a) Dynatrace UI → set cluster
   name/tokens → **Download dynakube.yaml**; (b) local → place at
   `secrets/dynatrace/dynakube.yaml`; (c) AWX → paste contents into the
   `Dynatrace-Dynakube` credential.

### Notes / risks

- The v1.9.0 cloud-native chart includes the CSI driver; validate on kind. The
  downloaded DynaKube may use classicFullStack/hostMonitoring — that is the
  user's file, not ours to change.
- OpenShift: pre-create ns with SCC annotations before the atomic install;
  OneAgent may need a privileged SCC (flag for OpenShift testing).
- `atomic: true` rolls back a failed operator install; the separate webhook wait
  guards the subsequent CR apply.
- `no_log: true` on all file/CR steps; `secrets/` gitignored; AWX stores the file
  encrypted.
- Chart `--version` is `1.9.0` (no `v`); the git tag is `v1.9.0`.

### Implementation notes (Dynatrace)

- Namespace is created and ownership-checked via `ensure_vendor_namespace.yaml`
  (no namespace `.j2` template).
- Wired into `install.yaml` / `uninstall.yaml` / `manage_tools.yaml`; uninstall
  is unconditional, idempotent, CSI-aware, and credential-independent.
- AWX: `dynatrace_injectors.json` (file injector) + `configure_credentials.yaml`
  (reconciled present/absent by enabled flag) + `node_tools_credentials.j2`
  (attached only to Deploy-Tools) + generated `argument_specs.j2`.
- The superseded `set_credentials_dynatrace.yaml` has been removed.
- Testing is **required**: `molecule/vendor_contract/` (credential-free) always
  runs; `molecule/deployment_vendors/` runs a live deploy when vendor secrets are
  provided and self-skips otherwise.

---

## Datadog (implemented) — operator + user-supplied `datadog-agent.yaml`

Datadog's onboarding UI produces a **non-secret** `datadog-agent.yaml`
(`DatadogAgent` CR) that references the API/APP keys **by Secret name** rather
than embedding them. So the split is:

- **Config (non-secret):** the `datadog-agent.yaml` (site, `clusterName`, feature
  toggles, RUM IDs). May be committed/pasted freely.
- **Secret:** `datadog-secret` with `api-key` / `app-key`, created separately. <!-- pragma: allowlist secret -->

This differs from Dynatrace (whose downloaded file embeds the tokens). We
therefore both consume the user's CR file **and** create the Secret from
`DATADOG_API_KEY` / `DATADOG_APP_KEY`.

### Decisions

- Consume the user's `datadog-agent.yaml` as-is (no re-templating).
- CR file source: variable `datadog_manifest_path` (env fallback via extra_var),
  default local path `secrets/datadog/datadog-agent.yaml` (gitignored). Under AWX
  it is injected as a file via a custom `Datadog` credential.
- Secret created by `set_credentials_datadog.yaml` from source-agnostic vars
  `datadog_api_key` / `datadog_app_key` (env fallback
  `DATADOG_API_KEY`/`DATADOG_APP_KEY`); `no_log: true`. Secret name and key names
  are configurable (`observability_vendors.datadog.{secret_name,api_key_name,app_key_name}`)
  and **must match** the `credentials.apiSecret/appSecret` refs in the CR.
- Helm: classic repo chart `datadog/datadog-operator` from
  `https://helm.datadoghq.com`, pinned `chart_version: 2.24.0`, `atomic: true`,
  `wait: true`. (The onboarding command uses the operator chart, not the agent
  chart.)
- Reuse `Deploy-Tools`/`Undeploy-Tools`; flag-gated by
  `tools_configuration.vendors.datadog.enabled`.

### Files (all created)

| File | Purpose |
|------|---------|
| `defaults/main/vendors.yaml` (datadog entry) | Operator chart `datadog-operator` @ `2.24.0`, ns `datadog` |
| `inventory/group_vars/environment/observability_vendors.yaml(.example)` | `datadog.{enabled,manifest_path,secret_name,api_key_name,app_key_name}` |
| `tasks/set_credentials_datadog.yaml` | Source-agnostic keys → create `datadog-secret` (`no_log`) |
| `templates/kubernetes/datadog/namespace.j2` | Namespace (OpenShift SCC annotations) |
| `tasks/install_datadog.yaml` | Resolve+assert manifest → ns → helm operator (atomic/wait) → wait for `datadogagents.datadoghq.com` CRD Established → create secret → apply CR file |
| `tasks/uninstall_datadog.yaml` | Delete DatadogAgent CRs → helm absent → delete ns |
| `tasks/install.yaml` / `uninstall.yaml` | Flag-gated import of Datadog tasks |
| `manage_tools.yaml` | `tools_configuration.vendors` from `observability_vendors` |
| `awx/files/awx/credential_types/datadog_injectors.json` | file→`datadog_manifest_path`; extra_vars→`datadog_api_key`/`datadog_app_key` |
| `awx/tasks/configure_credentials.yaml` | `Datadog` credential type + instance (gated on enabled) |
| `awx/templates/awx/workflows/node_credentials.j2` | Attach `Datadog` credential to Deploy/Undeploy-Tools nodes |
| `awx/meta/argument_specs.yaml` | Document `awx_configuration.vendors.datadog.*` |

### Install flow (`install_datadog.yaml`)

1. Resolve `datadog_manifest_path` (AWX extra_var/file, else group_var default).
2. `stat` + assert the manifest exists / non-empty.
3. Create namespace from `namespace.j2`.
4. Helm install `datadog-operator` (repo chart, `atomic: true`, `wait: true`).
5. Wait for the `datadogagents.datadoghq.com` CRD to be **Established**.
6. Import `set_credentials_datadog.yaml` → create `datadog-secret`.
7. Apply the user's `datadog-agent.yaml` (`from_yaml_all`), into the `datadog` ns.

### Usage

**Local:**
```bash
export DATADOG_API_KEY=...   # from the onboarding command  # pragma: allowlist secret
export DATADOG_APP_KEY=...   # optional, needed for Private Action Runner
mkdir -p scenarios/sre/secrets/datadog
cp ~/Downloads/datadog-agent.yaml scenarios/sre/secrets/datadog/datadog-agent.yaml
# set observability_vendors.datadog.enabled: true, then run Deploy-Tools
```

**AWX:** set `awx_configuration.vendors.datadog.{enabled: true, manifest: <file contents>, api_key, app_key}` so the `Datadog` credential is created and attached
to the Deploy-Tools node; also set `observability_vendors.datadog.enabled: true`
in the committed group_vars (the flag the playbook reads). AWX injects the
manifest as a file and the keys as extra_vars into the job pod.

### Notes / risks

- Secret key names must match the CR's `credentials.apiSecret.keyName` /
  `appSecret.keyName` (defaults `api-key` / `app-key`).
- The sample CR enables OTel collector host ports 4317/4318 and APM SSI —
  validate host-port availability and privileged access on kind/OpenShift.
- On OpenShift the node agent likely needs a privileged SCC (not yet added;
  flag for OpenShift testing) in addition to the namespace SCC annotations.
- App key is optional for basic monitoring but **required** for the Private
  Action Runner / "Agent to take action" feature shown in onboarding.
