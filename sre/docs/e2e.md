# End-to-End (E2E) Testing with AWX

This guide walks you through setting up and running end-to-end tests using AWX to allow for you to run multiple scenarios either on a local Kind cluster or on kOps clusters on AWS.

## Prerequisites

- Same as [here](https://github.com/itbench-hub/ITBench-Scenarios/blob/main/sre/README.md)
- Make

## Setup and Execution

### Step 1: Initialize Group Variables

Generate the required configuration files:

```bash
make -f Makefile.runner group_vars
```

This command creates four essential configuration files in the `group_vars/runner/` directory:

- **agent.yaml** - Agent configuration including LLM endpoints and API keys
- **credentials.yaml** - AWS credentials for cloud resources
- **experiments.yaml** - Scenario selection and trial configuration
- **github.yaml** - GitHub repository settings for test scenarios
- **stack.yaml** - Kubernetes configuration pointers (auto-populated)

### Step 2: Configure Group Variables

Update the generated configuration files according to your environment. See the [Configuration Reference](#configuration-reference) section below for detailed guidance.

### Step 3: Deploy AWX Stack

Install AWX on the selected cluster:

```bash
make -f Makefile.runner deploy_awx_stack
```

**Verify deployment** by checking that all pods are running:

```bash
kubectl get pods -n awx
```

Expected output:
```
NAME                                               READY   STATUS      RESTARTS   AGE
awx-deployment-migration-24.6.1-sbcb9              0/1     Completed   0          4h2m
awx-deployment-postgres-15-0                       1/1     Running     0          4h2m
awx-deployment-task-5df79dbc47-k8mcb               4/4     Running     0          4h2m
awx-deployment-web-744655bd58-q8958                3/3     Running     0          4h2m
awx-operator-controller-manager-645d4f8c74-pcd52   2/2     Running     0          4h3m
```

### Step 4: Access AWX Console

Open your browser and navigate to: [http://127.0.0.1:30950/ui_next/overview](http://127.0.0.1:30950/ui_next/overview)

**Login credentials:**
- Username: `admin`
- Password: Retrieve using the command below:

```bash
KUBECONFIG=<path_to_kubeconfig> kubectl get secret awx-deployment-admin-password -n awx --template={{.data.password}} | base64 -d
```

### Step 5: Configure AWX Pipeline

Set up job templates and workflows for your test scenarios:

```bash
make -f Makefile.runner configure_awx_pipeline
```

### Step 6: Launch Test Execution

Run your selected scenarios the specified number of times:

```bash
make -f Makefile.runner launch_experiment_workflow
```

### Step 7: Monitor Execution

After launching the workflow, monitor progress in the AWX console: [http://127.0.0.1:30950/ui_next/jobs?page=1&perPage=10&sort=-finished](http://127.0.0.1:30950/ui_next/jobs?page=1&perPage=10&sort=-finished)

### Step 8: Cleanup

Remove the AWX stack when testing is complete:

```bash
make -f Makefile.runner undeploy_awx_stack
```

## Configuration Reference

The group variable files control various aspects of AWX environment. Here's how to configure each file:

### Agent Configuration (agent.yaml)

Controls the SRE agent behavior and LLM integration. The ones below primarily go into effect while running the baseline ITBench SRE Agent provided [here](https://github.com/itbench-hub/ITBench-SRE-Agent).

```yaml
agent_configuration:
  version: "sre-agent-v1"
  configuration:
    agents_config:
      provider: "openai"              # LLM provider (openai, watsonx, etc.)
      model: "gpt-4o"                 # Model to use
      url: "https://api.openai.com/v1" # API endpoint
      api_key: "your-api-key-here"    # Your API key # pragma: allowlist secret
      seed: "42"                      # For reproducible results
      top_p: "0.1"                    # Sampling parameter
      temperature: "0.000001"         # Response randomness (lower = more deterministic)
      god_mode: true                  # Enable enhanced capabilities
    tools_config:
      # Similar configuration for tool-specific LLM usage
      provider: "openai"
      model: "gpt-4o"
      # ... (same parameters as agents_config)
    watsonx_config:
      wx_project_id: ""               # Required only if using watsonx
```

**Key settings to update:**
- Replace `api_key` with your actual OpenAI API key or alternate provider key
- Adjust `model` based on your subscription and requirements
- Modify `temperature` and `top_p` for desired response variability

### Credentials (credentials.yaml)

Configure AWS credentials for accessing cloud resources. This only needs to be configured for runs on AWS, not for local Kind cluster-based runs. Primarily the outputs from the experiment runs are uploaded.

```yaml
credentials:
  aws:
    access_key_id: "YOUR_ACCESS_KEY_ID"
    secret_access_key: "YOUR_SECRET_ACCESS_KEY" # pragma: allowlist secret
```

### Experiments (experiments.yaml)

List scenarios (referenced via scenario IDs) that are to be run and how many times (referreed to as trials):

```yaml
experiments:
  scenarios:
    - 1      # Uncomment scenarios you want to test
    # - 3
    # - 16
    # - 20
    # - 23
    # Add more scenario IDs as needed
  trials: 3  # Number of times to run each scenario
```

**Configuration tips:**
- The local Kind cluster setup supports one scenario at at time. There is a plan to extend this to allow for scenario runs one after the other.
- Increase `trials` for statistical significance
- Available scenarios and their respective scenario IDs in open source are documented [here](https://github.com/itbench-hub/ITBench-Scenarios/blob/main/sre/docs/incidents.md).

### GitHub Configuration (github.yaml)

Repository settings for test scenarios and agent code:

```yaml
github:
  it_bench:
    ssh:
      private_key_passphrase: "your-passphrase" # pragma: allowlist secret
      private_key_path: "/path/to/your/ssh/key"
    url: git@github.com:itbench-hub/ITBench-LeaderboardScenarios.git
    branch: v1-refactor-incidents
  llm_agent:
    url: https://github.com/itbench-hub/ITBench-SRE-Agent.git
    branch: switch-to-venv
```

**SSH key setup:**
- Generate an SSH key pair if you don't have one.
- Add the public key to your GitHub account
- Update `private_key_path` with your private key location
- Set `private_key_passphrase` if your key is encrypted
- The SSH key is setup is only needed if the repositories

### Stack Configuration (stack.yaml)

Kubernetes cluster configuration:

## For local Kind cluster based runs
```yaml
stack:
  awx:
    kubeconfig: ~/.kube/config       # Path to your local Kind clusters kubeconfig
  runners:
    kubeconfigs:
      - ~/.kube/config           # Path to your local Kind cluster kubeconfig with the appropriate host name
```

## For AWS based runs
Allows for multiple scenarios to run in across different available clusters. At this time we assume that each scenario has access to its own cluster.
