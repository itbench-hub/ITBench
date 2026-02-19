#!/bin/bash
set -e

ENDPOINT="${ENDPOINT}"
SERVICE_URL="${SERVICE_URL}"
BASELINE_RPS=${BASELINE_RPS}
SURGE_MULTIPLIER=${SURGE_MULTIPLIER}
SURGE_DURATION=${SURGE_DURATION}
RAMP_UP_TIME=${RAMP_UP_TIME}
PAYLOAD_SIZE_KB=${PAYLOAD_SIZE_KB}
METHOD="${METHOD}"

TARGET_RPS=$((BASELINE_RPS * SURGE_MULTIPLIER))
REQUESTS_PER_ITERATION=$((TARGET_RPS / 10))  # Iterate every 0.1 seconds
TOTAL_ITERATIONS=$((SURGE_DURATION * 10))

echo "=== Signing Request Surge Load Generator ==="
echo "Service: ${SERVICE_URL}${ENDPOINT}"
echo "Baseline RPS: ${BASELINE_RPS}"
echo "Surge RPS: ${TARGET_RPS} (${SURGE_MULTIPLIER}x)"
echo "Duration: ${SURGE_DURATION} seconds"
echo "Ramp-up: ${RAMP_UP_TIME} seconds"
echo "Payload size: ${PAYLOAD_SIZE_KB} KB"
echo "=========================================="

# Generate random payload
PAYLOAD=$(dd if=/dev/urandom bs=1024 count=${PAYLOAD_SIZE_KB} 2>/dev/null | base64)

# Ramp up phase
echo "Starting ramp-up phase..."
RAMP_ITERATIONS=$((RAMP_UP_TIME * 10))
for i in $(seq 1 $RAMP_ITERATIONS); do
  CURRENT_RPS=$((TARGET_RPS * i / RAMP_ITERATIONS / 10))
  for j in $(seq 1 $CURRENT_RPS); do
    curl -X ${METHOD} -H "Content-Type: application/json" \
         -d "{\"manifest\":\"${PAYLOAD:0:1000}\"}" \
         -s -o /dev/null -w "%{http_code}\n" \
         "${SERVICE_URL}${ENDPOINT}" >> /tmp/responses.log 2>&1 &
  done
  sleep 0.1
done

echo "Ramp-up complete. Starting sustained load..."

# Sustained load phase
for i in $(seq 1 $TOTAL_ITERATIONS); do
  for j in $(seq 1 $REQUESTS_PER_ITERATION); do
    curl -X ${METHOD} -H "Content-Type: application/json" \
         -d "{\"manifest\":\"${PAYLOAD:0:1000}\"}" \
         -s -o /dev/null -w "%{http_code}\n" \
         "${SERVICE_URL}${ENDPOINT}" >> /tmp/responses.log 2>&1 &
  done
  sleep 0.1

  # Progress reporting every 60 seconds
  if [ $((i % 600)) -eq 0 ]; then
    ELAPSED=$((i / 10))
    REMAINING=$((SURGE_DURATION - ELAPSED))
    RESPONSE_COUNT=$(wc -l < /tmp/responses.log 2>/dev/null || echo 0)
    echo "[${ELAPSED}s] Sent ${RESPONSE_COUNT} requests. ${REMAINING}s remaining..."
  fi
done

echo "Load generation complete!"
echo "Total requests sent: $(wc -l < /tmp/responses.log)"
echo "Response code distribution:"
sort /tmp/responses.log | uniq -c
