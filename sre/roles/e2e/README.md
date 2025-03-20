# For E2E Evaluation Runs

## One-time Setup
### Deploy AWX (and configure) (Ansible Tower)  to an existing cluster
1. Head to the parent directory under `IT-Automation-Test`
2. Ensure the following configurations are set under `group_vars/e2e.yaml`
    1. `awx_kubeconfig` path to the Kubeconfig cluster of the cluster to which you want to set up AWX
    2. Configurations under the `git` section
    3. Configurations under the `aws` section
3. To initalize AWX deployment run
```bash
make awx_setup
```
4. Once AWX is running,  let's run
```bash
make awx_configure_init
```
This sets up the `IT-Automation-Testbed` and `SRE-Agent` (Lumyn) GitHub repositories as projects, the custom execution environment for running each stage of the workflow and AWS credentials. 

5. URL to the deployed AWX instance can be accessed via
```bash
kubectl get service awx-deployment-service -n awx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```
and can be access by using the following credentials:
The `username` is `admin`
To get the `password` run:
```
KUBECONFIG=/path_to_awx_kubeconfig kubectl get secret awx-deployment-admin-password -n awx --template={{.data.password}} | base64 -d
```

## Every experiment run
### Cluster creation
Say you intend to run 20 scenarios. 
1. `cd` into `remote_cluster` and run (only for the first time):
```bash
cp playbooks/batch_variables.yaml.example playbooks/batch_variables.yaml
```
2. Update the `cluster_count` to 20 (whatever # of scenarios you intend to run) in `playbooks/batch_variables.yaml`. Update `instance_type`, `node_count` (worker node count) and any other variables as appropriate
3. Update the `s3name` at `playbooks/secret.yaml` if need be. This is the bucket which kOps would use store the Kubernetes configurations to be used in the running the experiment step. Please ensure the s3 bucket exists
4. Run
```bash
make batch_create
```

### Experiment Setup
1. Update the following configurations at `group_vars/e2e.yaml`
```
kops:
  s3_bucket_name: "bucket_with_cluster_credentials" # bucket which has the cluster credentials
scenarios:
  # list of scenarios which you intend to run
  - 1
  - 2
number_of_runs: 20 # number of runs / iterations per scenario

# configurations associated withe the agent configuration
agent_configuration:
  llm_for_agents_config:
```
2. `cd` into this directory `roles/e2e` and run:
```bash
python experiment_runner.py --experiment_spec ../../group_vars/e2e.yaml --batch_variables ../../remote_cluster/playbooks/batch_variables.yaml --path ../../
```
3. and enter "y". This would create the needed job templates and workflows for the experiment within AWX / Ansible Tower
4. Head over to the AWX endpoint to monitor the jobs if need be.
5. The experiment output is uploaded to the s3_bucket_name_for_results/lumyn-0.0.1/<run_id>. You can find the run_id by clicking the details page of any of the jobs in the awx console that were part of the experiment.

### Experiment Destruction
Once the experiment is complete
1. `cd` into this directory `roles/e2e` and run:
```bash
python experiment_runner.py --experiment_spec ../../group_vars/e2e.yaml --batch_variables ../../remote_cluster/playbooks/batch_variables.yaml --path ../../
```
2. and enter "n" (to nuke) this time. This would delete all the templates and workflows for the experiment within AWX / Ansible Tower

### Cluster Deletion
1. `cd` into `remote_cluster` and run:
```bash
make batch_delete
```
