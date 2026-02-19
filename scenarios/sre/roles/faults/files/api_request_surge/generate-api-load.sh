#!/bin/bash
set -e

RPS=${RPS}
DURATION=${DURATION}

echo "=== API Request Surge Load Generator ==="
echo "Target: Kubernetes API Server"
echo "Requests per second: ${RPS}"
echo "Duration: ${DURATION} seconds"
echo "=========================================="

TOTAL_REQUESTS=$((RPS * DURATION))
COUNT=0
START_TIME=$(date +%s)

# Simple operation: LIST pods in all namespaces
while [ $COUNT -lt $TOTAL_REQUESTS ]; do
  ELAPSED=$(($(date +%s) - START_TIME))
  
  if [ $ELAPSED -ge $DURATION ]; then
    break
  fi
  
  # Simple operation: LIST pods in all namespaces
  kubectl get pods --all-namespaces -o name > /dev/null 2>&1 &
  
  COUNT=$((COUNT + 1))
  
  # Progress reporting every 10 seconds
  if [ $((COUNT % (RPS * 10))) -eq 0 ]; then
    REMAINING=$((DURATION - ELAPSED))
    echo "[${ELAPSED}s] Sent ${COUNT} requests. ${REMAINING}s remaining..."
  fi
  
  # Sleep to maintain desired RPS
  sleep $(awk "BEGIN {print 1/${RPS}}")
done

echo "Load generation complete!"
echo "Total requests sent: ${COUNT}"
echo "Actual duration: $(($(date +%s) - START_TIME))s"
