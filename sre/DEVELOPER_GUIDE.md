# Developer Guide

## Running Incident Scenarios - Step-by-Step Guide
This section provides detailed instructions for each phase of running an incident scenario:
1. **Deploy observability and chaos engineering tools**
2. **Deploy sample applications**
3. **Inject fault/failure mechanisms**
4. **Monitor the outcomes**

### Step 1: Deploy Observability Stack

Deploy the complete observability, monitoring and chaos engineering toolkit:

```bash
make deploy_tools
```

**What gets deployed:**
- **Prometheus** - Metrics collection and alerting
- **ClickHouse** - Analytics database
- **OpenSearch** - Log aggregation and Kubernetes events
- **Jaeger** - Tracing
- **Chaos Mesh** - Chaos engineering platform
- **OpenCost** - Cost monitoring
- **Kubernetes Metrics Server** - Resource metrics

#### FinOps Configuration (Optional)
For financial operations (FinOps) scenarios, update `group_vars/environment/tools.yaml` before deploying:

```yaml
tools:
  kubernetes_metrics_server: true
  opencost: true
```

**Additional details:** [Tools documentation](./docs/tools.md)

### Step 2: Deploy Sample Application

Deploy the default Astronomy Shop application:

```bash
make deploy_applications
```

**Additional details:** [Sample applications documentation](./docs/applications.md)

### Step 3: Inject Incident Fault

Once all pods are running, inject the fault for your chosen incident:

```bash
INCIDENT_NUMBER=1 make inject_incident_fault
```

**Open-sourced incident scenarios:** 1, 3, 23, 26, 27, 102

**Additional details:** [Incident scenarios and fault mechanisms](./docs/incidents.md)

### Step 4. Set Up Port Forwarding
Enable access to the Prometheus and Jaeger dashboards:

```bash
kubectl port-forward svc/ingress-nginx-controller -n ingress-nginx 8080:80 &
```

### Step 5. Access Dashboards
Navigate to the following URLs in your browser:

```bash
# View alerts and metrics
http://localhost:8080/prometheus/alerts

# View traces
http://localhost:8080/jaeger
```

### Step 6. Monitor Alert States
The system includes alerts that monitor:
- Deployment status across namespaces
- Service latency metrics
- Error rates across services
- Kafka connection statuses

**Alert Behavior:**
- Default state: `Inactive`
- After a few minutes: `Firing` (indicating fault manifestation)

### Step 7. SRE Agent Configuration (Optional)
If using the [SRE-Agent](https://github.com/itbench-hub/itbench-sre-agent), configure your `.env.tmpl` file:

### Step 8: Complete Cleanup

Remove all deployed components:

```bash
make undeploy_applications
make undeploy_tools
```
