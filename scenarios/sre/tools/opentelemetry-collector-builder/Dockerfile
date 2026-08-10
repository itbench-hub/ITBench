FROM registry.access.redhat.com/ubi10-minimal:10.2-1786323476@sha256:e6c7c01447dc8eadf2a673e65fb6c607f16e168fe29a776fb937004f33c81cc0 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1786353903@sha256:cc3a002ecdb1b7e6e0e2988333b257eb97cfce84dbdfc98f4e02297c9190c4e1 AS builder

ENV CGO_ENABLED=0

WORKDIR /workspace/builder

COPY go.mod go.mod
COPY go.sum go.sum

RUN go mod download

COPY builder-config.yaml builder-config.yaml

RUN go tool builder --config builder-config.yaml

FROM gcr.io/distroless/static-debian13:nonroot

COPY --chmod=555 --from=certs /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem /etc/ssl/certs/ca-certificates.crt

WORKDIR /

COPY --chmod=755 --from=builder /workspace/opentelemetry-collector/it-bench-otelcollector it-bench-otelcollector

ENTRYPOINT ["/it-bench-otelcollector"]

EXPOSE 4317 4318
