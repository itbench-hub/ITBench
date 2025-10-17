# How to Launch the Benchmark (CISO Agent)

This guide walks you through launching the ITBench benchmark for a CISO agent.  
You will run two Docker containers—**Agent Harness** and **Bench Runner**—and keep them running during the evaluation.

> ⚠️ **Note:** You must not run multiple Agent Harnesses or Bench Runners at the same time.

## Option 1: Use the CISO CAA Agent (Prebuilt)

If you would like to benchmark using the [official CISO CAA Agent](https://github.com/itbench-hub/itbench-ciso-caa-agent), follow these steps:

1. Create a .env File
    Create a .env file with the following contents:
    ```
    OPENAI_API_KEY = <YOUR OPENAI API KEY>
    OPENAI_MODEL_NAME = gpt-4o-mini
    CODE_GEN_MODEL = gpt-4o-mini
    ```
    If you want to use other models, refer to [this section](https://github.com/itbench-hub/itbench-ciso-caa-agent?tab=readme-ov-file#3-create-env-file-and-set-llm-api-credentials)

1. Run CISO Agent Harness Docker container
    Run the container, replacing `<ABSOLUTE_PATH/TO/AGENT_MANIFEST>` and `<ABSOLUTE_PATH/TO/ENVFILE>` replaced with your own paths.
    ```
    docker run --rm -it --name ciso-agent-harness \
        --mount type=bind,src=<ABSOLUTE_PATH/TO/AGENT_MANIFEST>,dst=/tmp/agent-manifest.json \
        --mount type=bind,src=<ABSOLUTE_PATH/TO/ENVFILE>,dst=/etc/ciso-agent/.env \
        quay.io/it-bench/ciso-agent-harness:latest \
        --host itbench.apps.prod.itbench.res.ibm.com \
        --benchmark_timeout 3600
    ```
    <img width="614" alt="image" src="https://github.com/user-attachments/assets/a41eaa4d-9770-4637-88ed-3c487893a2e1">

1. Run the CISO DEF Runner Docker Container
    Open a new terminal window and run the container, replacing `<ABSOLUTE_PATH/TO/AGENT_MANIFEST>` and `<ABSOLUTE_PATH/TO/KUBECONFIG_FILE>` replaced with your own paths.
    
    (If you are benchmarking a RHEL scenario, please refer to [the full specification.](#full-specification-of-bench-runner))
    ```
    docker run --rm -it --name ciso-bench-runner \
        --mount type=bind,src=<ABSOLUTE_PATH/TO/AGENT_MANIFEST>,dst=/tmp/agent-manifest.json \
        --mount type=bind,src=<ABSOLUTE_PATH/TO/KUBECONFIG_FILE>,dst=/tmp/kubeconfig.yaml \
        quay.io/it-bench/ciso-bench-runner:latest \
        --host itbench.apps.prod.itbench.res.ibm.com \
        --runner_id my-ciso-runner-1
    ```
    <img width="614" alt="image" src="https://github.com/user-attachments/assets/8dc70982-2219-4bd5-ae85-5845e07818cd">

1. Benchmark Progress and Status Updates
    - The benchmark will proceed automatically after starting:
        - The benchmark will typically complete within about one hour, after which both Docker containers will exit automatically.
        - Once completed, you can safely close both terminal windows.
    - During the benchmark:
        - The original registration issue will be updated approximately every 10 minutes.
        - A table summarizing the results will appear, showing the status of each scenario.
    
    <img width="614" alt="image" src="https://github.com/user-attachments/assets/e59a0a9f-6d2a-496c-9479-e779c391f312">

Table Fields:
| Field             | Description                                         |
|:------------------|:----------------------------------------------------|
| Scenario Name     | The name of the scenario                            |
| Description       | A short description of the control being assessed   |
| Passed            | Whether the agent passed the scenario (True/False)  |
| Time To Resolve   | Time taken to complete                              |
| Error             | Any unexpected error encountered                    |
| Message           | Additional information or status                    |
| Date              | Completion timestamp                                |

5. Once all scenarios are completed:
    - The Docker commands will automatically stop.
        
        <img width="619" alt="command-done" src="https://github.com/user-attachments/assets/f1509c35-c5e2-4486-a2db-0ac486cdc7b7">

    - The registration issue comment will update its status to **Finished**, and the issue will automatically close.

        <img width="586" alt="issue-close" src="https://github.com/user-attachments/assets/592f1152-8072-4c85-bc9f-6fddeae34fdd">

6. Troubleshooting
    
    - If the benchmark fails to start:
        - Add a comment to the issue with the text abort.
        - Optionally, include additional notes about the problem.
    
    - If the containers keep running without completing:
        - Check if the "Date" field in the table is not updating.
        - If it is stuck, terminate the container processes manually (Ctrl+C) and add abort to the issue comment.

7. Leaderboard Update:
    - The benchmark results will be manually reflected on the leaderboard within a few days.

        <img width="614" alt="image" src="https://github.com/user-attachments/assets/4edcaf57-38b9-4107-9098-3dfd2ffa493e">

    - If you do not see updates after a few days, please reach out to [Contact Support](#contact-support).


## Option 2: Use Your Own Agent

If you are submitting your own custom agent, follow these steps:

1. Create Agent Harness config
    ```yaml
    # This field defines the path where the scenario's environment information is stored.
    # When the agent harness runs the command below, the scenario data is fetched from the server and saved at this location.
    path_to_data_provided_by_scenario: /tmp/agent/scenario_data.json 
    
    # This field defines the path where the agent's output results should be stored.
    # The agent harness uploads this file back to the server for evaluation.
    path_to_data_pushed_to_scenario: /tmp/agent/agent_data.txt 
    
    # Command to be run by the agent harness
    run:
      command: ["/bin/bash"]
      args:
      - -c
      - |
        <your command to run Agent>
    ```

    The `command` is executed with `args` inside a docker container that is built from a Dockerfile you create (we will instruct in the later section).

    For example, the following is [the Agent Harness config](https://github.com/itbench-hub/ITBench-CISO-CAA-Agent/blob/main/agent-harness.yaml) of the sample CISO CAA Agent. It appears complex because it includes error handling. When creating your own harness config, it doesn’t need to be this complicated. However, make sure to include proper termination handling to avoid infinite loops.
    
    ```yaml
    path_to_data_provided_by_scenario: /tmp/agent/scenario_data.json
    path_to_data_pushed_to_scenario: /tmp/agent/agent_data.tar
    run:
    command: ["/bin/bash"]
    args:
    - -c
    - |
    
        timestamp=$(date +%Y%m%d%H%M%S)
        tmpdir=/tmp/agent/${timestamp}
        mkdir -p ${tmpdir}

        cat /tmp/agent/scenario_data.json > ${tmpdir}/scenario_data.json

        jq -r .goal_template ${tmpdir}/scenario_data.json > ${tmpdir}/goal_template.txt
        jq -r .vars.kubeconfig ${tmpdir}/scenario_data.json > ${tmpdir}/kubeconfig.yaml
        jq -r .vars.ansible_ini ${tmpdir}/scenario_data.json > ${tmpdir}/ansible.ini
        jq -r .vars.ansible_user_key ${tmpdir}/scenario_data.json > ${tmpdir}/user_key
        chmod 600 ${tmpdir}/user_key
        sed -i.bak -E "s|(ansible_ssh_private_key_file=\")[^\"]*|\1${tmpdir}/user_key|" ${tmpdir}/ansible.ini
        
        sed "s|{{ kubeconfig }}|${tmpdir}/kubeconfig.yaml|g" ${tmpdir}/goal_template.txt > ${tmpdir}/goal.txt
        sed -i.bak -E "s|\{\{ path_to_inventory \}\}|${tmpdir}/ansible.ini|g" ${tmpdir}/goal.txt

        echo "You can use \`${tmpdir}\` as your workdir." >> ${tmpdir}/goal.txt
        
        source .venv/bin/activate
        timeout 200 python src/ciso_agent/main.py --goal "`cat ${tmpdir}/goal.txt`" --auto-approve -o ${tmpdir}/agent-result.json || true

        tar -C ${tmpdir} -cf /tmp/agent/agent_data.tar .
    ```

        1. Timestamped Temporary Directory Creation
            ```
            timestamp=$(date +%Y%m%d%H%M%S)
            tmpdir=/tmp/agent/${timestamp}
            mkdir -p ${tmpdir}
            ```
        2. Scenario Data Processing
            ```
            cat /tmp/agent/scenario_data.json > ${tmpdir}/scenario_data.json
            ```
            Copies the downloaded scenario data from IT Bench, which is specified in `path_to_data_provided_by_scenario`, into the temporary directory.
        3. Extracting Key Variables to be passed to python command arguments to run the CISO CAA Agent
            ```
            jq -r .goal_template ${tmpdir}/scenario_data.json > ${tmpdir}/goal_template.txt
            jq -r .vars.kubeconfig ${tmpdir}/scenario_data.json > ${tmpdir}/kubeconfig.yaml
            jq -r .vars.ansible_ini ${tmpdir}/scenario_data.json > ${tmpdir}/ansible.ini
            jq -r .vars.ansible_user_key ${tmpdir}/scenario_data.json > ${tmpdir}/user_key
            chmod 600 ${tmpdir}/user_key
            ```
    
        4. Updating ansible.ini with User Key for RHEL scenario cases.
            ```
            sed -i.bak -E "s|(ansible_ssh_private_key_file=\")[^\"]*|\1${tmpdir}/user_key|" ${tmpdir}/ansible.ini
            ```
        5. Preparing the Goal File to be passed to python command arguments to run the CISO CAA Agent
            ```
            sed "s|{{ kubeconfig }}|${tmpdir}/kubeconfig.yaml|g" ${tmpdir}/goal_template.txt > ${tmpdir}/goal.txt
            sed -i.bak -E "s|\{\{ path_to_inventory \}\}|${tmpdir}/ansible.ini|g" ${tmpdir}/goal.txt
            echo "You can use \`${tmpdir}\` as your workdir." >> ${tmpdir}/goal.txt
            ```
        6. Running the Agent (Automated or Manual)
            ```
            source .venv/bin/activate
            timeout 200 python src/ciso_agent/main.py --goal "`cat ${tmpdir}/goal.txt`" --auto-approve -o ${tmpdir}/agent-result.json || true
            ```
            - Enable python virtual env
            - Runs main.py with the goal extracted from goal.txt.
            - Enforces a timeout of 200 seconds to avoid infinite running.
            - Saves the result as agent-result.json in `${tmpdir}` directory.
        7. Archiving the Execution Data by the agent
            The CISO CAA Agent generates compliance policy programs and stores them in the designated working directory. The script ensures that all relevant execution data is archived for further analysis.
            ```
            tar -C ${tmpdir} -cf /tmp/agent/agent_data.tar .
            ```
1. Create a Docker image
    The docker image is built from Agent Harness base image and is expected to contain your Agent (e.g. crewai python program).
    
    For example, the Dockerfile is as follows in the case of CISO Agent:
    ```
    FROM icr.io/agent-bench/ciso-agent-harness-base:0.0.3 AS base
    RUN ln -sf /bin/bash /bin/sh
    RUN apt update -y && apt install -y curl gnupg2 unzip ssh

    # install dependencies here to avoid too much build time
    COPY itbench-ciso-caa-agent /etc/ciso-agent
    WORKDIR /etc/ciso-agent
    RUN python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt --no-cache-dir

    # install `ansible-playbook`
    RUN pip install --upgrade ansible-core jmespath kubernetes==31.0.0 setuptools==70.0.0 --no-cache-dir
    RUN ansible-galaxy collection install kubernetes.core community.crypto
    RUN echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config
    # install `jq`
    RUN apt update -y && apt install -y jq
    # install `kubectl`
    RUN curl -LO https://dl.k8s.io/release/v1.31.0/bin/linux/$(dpkg --print-architecture)/kubectl && \
        chmod +x ./kubectl && \
        mv ./kubectl /usr/local/bin/kubectl
    # install `aws` (need this for using kubectl against AWS cluster)
    RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o "awscliv2.zip" && \
        unzip awscliv2.zip && \
        ./aws/install
    # install `opa`
    RUN curl -L -o opa https://github.com/open-policy-agent/opa/releases/download/v1.0.0/opa_linux_$(dpkg --print-architecture)_static && \
        chmod +x ./opa && \
        mv ./opa /usr/local/bin/opa

    RUN python -m venv .venv && source .venv/bin/activate && pip install -e /etc/ciso-agent --no-cache-dir

    COPY agent-bench-automation.wiki/.gist/agent-harness/entrypoint.sh /etc/entrypoint.sh
    RUN chmod +x /etc/entrypoint.sh
    WORKDIR /etc/agent-benchmark

    ENTRYPOINT ["/etc/entrypoint.sh"]
    ```

## Conclusion

Congratulations! You’ve successfully completed the ITBench benchmarking process.

## Contact Support

If you do not receive any response within a couple of days, please leave a comment in your original registration issue and mention our support team.
    - Mention: @yana, @rohanarora
    - Add Label: `need help`

Example Comment:
```
@yana, @rohanarora
Hi, I have not received a response regarding my registration request.
Adding the "need help" label for visibility.
```

## Misc

#### Full Specification of Bench Runner

```
docker run --rm -it --name ciso-bench-runner \
    --mount type=bind,src=<ABSOLUTE_PATH/TO/AGENT_MANIFEST>,dst=/tmp/agent-manifest.json \
    --mount type=bind,src=<ABSOLUTE_PATH/TO/KUBECONFIG_FILE>,dst=/tmp/kubeconfig.yaml \
    --mount type=bind,src=<PATH/TO/RHEL_MACHINE_SSHKEY>,dst=/tmp/rhel-bundle-config/ssh_key \
    quay.io/it-bench/ciso-bench-runner:latest \
    --host itbench.apps.prod.itbench.res.ibm.com \
    --runner_id my-ciso-runner-1 \
    --rhel_address <IP Address or Hostname of the RHEL9 machine used for RHEL Scenario> \
    --rhel_username <Username of the RHEL9 machine used for RHEL Scenario>
```