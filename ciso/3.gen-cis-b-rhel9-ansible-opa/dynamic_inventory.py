#!/usr/bin/env python3
# Copyright contributors to the ITBench project. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

input_file = os.getenv("BUNDLE_INPUT_FILE", "input.json")
with open(input_file, "r") as f:
    input = json.load(f)

inventory_host = input["inventory_host"]
target_server = input["target_server"]
host_alias = target_server["alias"]
username = target_server["username"]
server_address = target_server["address"]
server_sshkey = target_server["sshkey"]

inventory = {
    inventory_host: {
        "hosts": [host_alias],
        "vars": {
            "ansible_user": username,
            "ansible_ssh_private_key_file": server_sshkey,
            "ansible_ssh_common_args": "-o StrictHostKeyChecking=no",
        },
    },
    "_meta": {"hostvars": {host_alias: {"ansible_host": server_address}}},
}

print(json.dumps(inventory))
