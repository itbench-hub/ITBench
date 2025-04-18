# ITBench: SRE Incident and FinOps Scenarios

Currently, ITBench comprises of an initial set of 42 SRE scenarios and 2 FinOps scenarios. The following scenarios are being open-sourced at this time and their implementation can be found [here](../roles):

| ID | Name | Platform | DSL Format | Description | Application | Complexity | Technologies | Golden Signal Cause | Golden Signal Effect |
|---|---|---|---|---|---|---|---|---|---|
| [1](#id-1-recommendation-service-cache) | Recommendation Service Cache | kubernetes | groups | Recommendation Service in Astronomy Shop has a cache failure | otel_astronomy_shop | Medium | Python, Node.js | saturation | error |
| [3](#id-3-ad-service-cpu) | Ad Service CPU | kubernetes | groups | Ad Service in Astronomy Shop runs with high CPU load | otel_astronomy_shop | Medium | Java, Node.js | saturation | error |
| [23](#id-23-checkoutservice-corrupt-image) | Checkoutservice Corrupt Image | kubernetes | groups | checkoutserviceCorruptDeployment: modify the checkoutservice image to unsupported image (arm64) instead of amd64 image | otel_astronomy_shop | Low | Node.js | resource unavailability | error |
| [26](#id-26-http-request-tamper-fault) | HTTP request tamper fault | kubernetes | groups | Modify HTTP POST requests from checkoutservice to emailservice | otel_astronomy_shop | Medium | Go, Ruby | traffic | error |
| [27](#id-27-abort-http-request-fault) | Abort HTTP request fault | kubernetes | groups | Aborts HTTP requests to quoteservice using chaos mesh fault | otel_astronomy_shop | High | Go, PHP, Rust, Tonic | traffic | error |
| [102](#id-102-memory-resource-limit-issue) | Memory quota on namespace | kubernetes | groups | (empty) | deathstarbench_hotel_reservations | Low | Go, Node.js | resource unavailability | error |

## Detailed Incident Scenario Information

### [ID 1: Recommendation Service Cache](../roles/incident_1/tasks/main.yaml)

**Fault Details:**
- Frontend service experiencing high HTTP error rate
- Recommendation service experiencing high HTTP error rate
- Feature flag `recommendationCacheFailure` set to "on" in flagd configuration

**Alerts:**
- Error Rate Above Threshold (frontend-service-1)

**Recommended Actions:**
1. Disable recommendationCacheFailure feature flag
2. Increase Memory Allocation

### [ID 3: Ad Service CPU](../roles/incident_3/tasks/main.yaml)

**Fault Details:**
- Frontend service experiencing high HTTP error rate
- Cart service experiencing high HTTP error rate
- Feature flag `adHighCpu` set to "on" in flagd configuration

**Alerts:**
- Error Rate Above Threshold (frontend-service-1)

**Recommended Actions:**
- Disable adHighCpu feature flag

### [ID 23: CheckoutService Corrupt Image](../roles/incident_23/tasks/main.yaml)

**Fault Details:**
- Checkout pod in ImagePullBackOff state due to incorrect architecture image

**Alerts:**
- Error Rate Above Threshold (frontend-service-1)

**Recommended Actions:**
- Change the image of checkout to correct image for amd64 system

### [ID 26: HTTP request tamper fault](../roles/incident_26/tasks/main.yaml)

**Fault Details:**
- HTTP POST request body tampering between checkoutservice and emailservice
- Affects /api/send_order_confirmation endpoint

**Alerts:**
- Error Rate Above Threshold (checkout-service-1)
- Error Rate Above Threshold (email-service-1)

**Recommended Actions:**
- Delete the resource httpchaos tamper-body-otel-demo-26-emailservice

### [ID 27: Abort HTTP request fault](../roles/incident_27/tasks/main.yaml)

**Fault Details:**
- HTTP requests to quoteservice being aborted
- Affects all POST requests to /getquote endpoint

**Alerts:**
- Error Rate Above Threshold (frontend-service-1)
- Error Rate Above Threshold (checkout-service-1)
- Error Rate Above Threshold (shipping-service-1)

**Recommended Actions:**
- Delete the resource httpchaos on quoteservice

### [ID 102: Memory Resource Limit Issue](../roles/incident_102/tasks/main.yaml)

**Fault Details:**
- Search pod experiencing resource constraints
- Search service replicaset has 0 pods

**Alerts:**
- Error Rate Above Threshold (frontend-service-1)

**Recommended Actions:**
- Increase memory resource limit
