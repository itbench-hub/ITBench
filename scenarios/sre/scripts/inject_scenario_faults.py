import argparse
import logging
import os
import sys
import time

import ansible_runner
import yaml

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

logger = logging.getLogger(__name__)

# Argument Parsing
parser = argparse.ArgumentParser(
    description="CLI for asynchronous fault injection for live ITBench SRE and FinOps scenarios"
)
parser.add_argument(
    "--private_project_directory",
    help="path to the directory of the project",
    required=True,
    type=str
)
parser.add_argument(
    "--scenario_id",
    help="identifier for scenario",
    required=True,
    type=int
)

def main():
    args = parser.parse_args()

    try:
        file_path = os.path.join(
            args.private_project_directory,
            "project",
            "roles",
            "scenarios",
            "files",
            "scenario_{0}".format(args.scenario_id),
            "scenario.yaml"
        )

        spec = {}
        with open(file_path) as f:
            spec = yaml.safe_load(f)
    except:
        logger.exception("scenario spec loading failure: {0}".format(sys.exception()))
        sys.exit("error: scenario spec failed to load.")

    runners = []

    for fault_index in range(0, len(spec["spec"]["faults"])):
        logger.info("start fault tasks for group {0}".format(fault_index + 1))

        _, runner = ansible_runner.interface.run_async(
            private_data_dir=args.private_project_directory,
            playbook="manage_faults.yaml",
            ident="scenario-{0}-fault-{1}".format(
                args.scenario_id,
                fault_index
            ),
            cmdline="--tags inject_faults --extra-vars scenario_id={0} --extra-vars fault_index={1}".format(
                args.scenario_id,
                fault_index
            )
        )
        runners.append(runner)

    for r in runners:
        logger.debug("waiting for runner to complete tasks")

        while r.status not in ["canceled", "successful", "timeout", "failed"]:
            time.sleep(1)
            continue

    logger.info("all fault tasks have been completed")

if __name__ == "__main__":
    main()
