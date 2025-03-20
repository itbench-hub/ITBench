# Incident Reporting

The goal of creating standardized incident documentation fields is to support high-level reports.

These tables map the fields to their reasons.

| Old Field Name                       | Type    | Detail                                                                    |
| :---                                 | :---    | :---                                                                      |
| ID                                   | integer | Required for administration                                               |
| application                          | string  | ['otel_astronomy_shop', 'deathstarbench_hotel_reservations', 'Other']     |
| fault[].entity.name                  | string  | User ID if kind is "User"; Kubernetes object name otherwise               |
| fault[].entity.kind                  | string  | [ "User", "Pod", "Service", "Deployment", "Node", "ConfigMap", "Other" ]  |
| fault[].entity.changed.element       | string  | dot-separated path (`\.` to escape dots) within Kubernetes object.        |
| fault[].entity.changed.from          | string  |                                                                           |
| fault[].entity.changed.to            | string  |                                                                           |
| fault[].entity.comment               | string  | Optional (should be included if kind is "Other")                          |
| fault[].condition                    | string  | Human-readable description of the fault.                                  |
| manual_actions                       | array   | Human-readable description of remediation action that would work          |
| automations                          | array   |                                                                           |
| scenario.complexity                  | string  | Either "Low", "Medium", or "High"                                         |
| scenario.inject_fault_unused         | boolean |                                                                           |
| scenario.agent_operation_timeout_sec | integer | Maximum number of seconds before giving up on remedial action succeeding. |


| Report Goal                          | Primary Fields Used           |
| :---                                 | :---                          |
| Caused by change coverage            | fault[].due_to_change         |
| Application-use                      | application                   |
| Fault element distribution           | fault[].entity.kind           |

## Example variable settings

```
      "id": 1
      "application": "otel_astronomy_shop"
      "scenario":
        "complexity": "Low"
        "inject_fault_unused": false
        "agent_operation_timeout_sec": 3000
      "fault":
        - "entity":
            "name": "otel-demo-checkoutservice"
            "kind": "Deployment"
          "condition": "cache utilization high"
      "manual_actions": 
        - "increase memory"
        - "kill leaking process"
      "automations":
        - "auto one"
        - "auto two"
```

```
      "id": 2
      "application": "Other"
      "scenario":
        "complexity": "Low"
        "inject_fault_unused": false
        "agent_operation_timeout_sec": 3000
      "fault":
        - "entity":
            "name": "not-yet-provided"
            "kind": "Other"
            "comment": "Please identify the Kubernetes object here."
          "condition": "Please fill in"
      "manual_actions":
        - "valid action 1"
        - "valid action 2"
      "automations":
        - "auto one"
        - "auto two"
```

```
      "id": 3
      "application": "otel_astronomy_shop"
      "scenario":
        "complexity": "Low"
        "inject_fault_unused": false
        "agent_operation_timeout_sec": 3000
      "fault":
        - "entity":
            "name": "<fault_pod_checkoutservice_1>"
            "kind": "Pod"
            "changed":
              "element": "spec.containers[0].env[3].value"
              "from": "8080"
              "to": "8000"
            "comment": "changed env CHECKOUT_SERVICE_PORT"
          "condition": "Please fill in"
          "due_to_user_payload": "no"
        - "entity":
            "name": "root"
            "kind": "User"
            "comment": "Something specific that user root did."
          "condition": "Please fill in"
      "manual_actions":
        - "valid action 1"
        - "valid action 2"
      "automations":
        - "auto one"
        - "auto two"
```
