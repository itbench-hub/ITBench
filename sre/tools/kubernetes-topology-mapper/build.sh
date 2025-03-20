#!/bin/sh
podman manifest create quay.io/it-bench/topology-monitor:latest
podman build --platform linux/amd64,linux/arm64 -f Dockerfile --manifest quay.io/it-bench/topology-monitor:latest
podman manifest push quay.io/it-bench/topology-monitor:latest
