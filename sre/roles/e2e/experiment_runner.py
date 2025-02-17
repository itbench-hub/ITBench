import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from experiment_models import AWXConfigurationModel, ExperimentModel
from experiment_utils import load_yaml


# Temp fix until scneario_spec is implemented
sample_application_HOTEL_RESERVATIONS_SCENARIOS = [102, 210, 211, 212]


class ExperimentRunner:

    def __init__(self, experiment_config: Path, path_to_base_playbook_directory: Path, state: str = "present"):
        self.experiment_config = load_yaml(experiment_config)
        self.experiment = ExperimentModel(**self.experiment_config)
        self.base_yaml = os.path.join(path_to_base_playbook_directory, "base.yaml")
        self.state = state

    def setup(self):
        run_uuid = str(uuid.uuid4())

        # Get list of current clusters
        list_clusters_command = subprocess.run(
            f"kops get clusters --state s3://{self.experiment.kops.s3_bucket_name} | awk '{{print $1}}' | tail -n +2",
            shell=True,
            check=True,
            stdout=subprocess.PIPE)
        if list_clusters_command.returncode != 0:
            raise SystemExit

        relevant_clusters = [
            each_cluster for each_cluster in
            list_clusters_command.stdout.decode("utf-8").splitlines()
            if "exp-runner" in each_cluster.lower()
        ]

        if len(relevant_clusters) < len(self.experiment.scenarios):
            raise SystemExit(
                "Insufficent number of clusters to run the desired experiment."
            )

        counter = 0
        mapping = {
            1: 1,
            3: 2,
            5: 3,
            6: 4,
            12: 5,
            14: 6,
            15: 7,
            16: 8,
            17: 9,
            18: 10,
            19: 11,
            20: 12,
            23: 13,
            25: 14,
            26: 15,
            27: 16,
            28: 17,
            29: 18,
            32: 19,
            34: 20,
            102: 21
        }
        for each_scenario in self.experiment.scenarios:
            # ToDo: To pick up cluster annotated name and instance_type from bucket
            cluster_assignment = f"exp-runner-m4.xlarge-aws-{mapping[each_scenario]}.k8s.local"

            # get relevant Kubeconfig(s)
            kubeconfig_command = subprocess.run(
                f"KOPS_STATE_STORE=s3://{self.experiment.kops.s3_bucket_name} kops export kubecfg {cluster_assignment} --admin=36h0m0s --kubeconfig /tmp/{cluster_assignment}.yaml",
                shell=True,
                check=True)
            if kubeconfig_command.returncode != 0:
                raise SystemExit

            sample_application = "otel_astronomy_shop"
            if each_scenario in sample_application_HOTEL_RESERVATIONS_SCENARIOS:
                sample_application = "dsb_hotel_reservation"

            job_template_creation = subprocess.run(
                f"ansible-playbook -v {self.base_yaml} --tags \"awx_scenario_setup\" --extra-vars \"relevant_kubeconfig_file_path=/tmp/{cluster_assignment}.yaml scenario_number={each_scenario} domain=sre state={self.state} sample_application={sample_application}\"",
                shell=True,
                check=True)
            if job_template_creation.returncode != 0:
                raise SystemExit

            workflow_template_creation = subprocess.run(
                f"ansible-playbook -v {self.base_yaml} --tags \"workflow_setup\" --extra-vars \"scenario_number={each_scenario} state={self.state} sample_application={sample_application}\"",
                shell=True,
                check=True)
            if workflow_template_creation.returncode != 0:
                raise SystemExit

            if state == "present":
                launch_workflow_command = subprocess.run(
                    f"ansible-playbook -v {self.base_yaml} --tags \"workflow_launch\" --extra-vars \"run_uuid={run_uuid} sre_agent_name__version_number=lumyn-0.0.1 scenario_number={each_scenario} number_of_runs={self.experiment.number_of_runs} state={self.state} sample_application={sample_application}\"",
                    shell=True,
                    check=True)
                if launch_workflow_command.returncode != 0:
                    raise SystemExit
            # To prevent AWX error due to API Limit(?)
            time.sleep(30)
            counter += 1


class AddErrorParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


if __name__ == "__main__":
    parser = AddErrorParser()
    parser.add_argument('--experiment_spec', help='path to the experiment file', required=True)
    parser.add_argument('--path', help='path to the playbook directory', required=True)
    arguments = parser.parse_args()

    init_or_deinit = input("Are you looking to initialize the experiment or nuke it? y to initialize, n to nuke\n")
    if init_or_deinit.lower() == "y":
        state = "present"
    elif init_or_deinit.lower() == "n":
        state = "absent"
    else:
        print("Please enter a valid input")
        raise SystemExit

    experiment = ExperimentRunner(arguments.experiment_spec, arguments.path, state=state)
    experiment.setup()
