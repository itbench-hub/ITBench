FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:552f8cc1ddb0bc9e411065c78499aa4dbc2c4ea9bd057aa0e6e44940db13acb5 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1792406018@sha256:78049192391115cdcc3a794bf0e7295a1f54fbb110c0a832e6b1254dbd15239d AS builder

ENV CGO_ENABLED=0

WORKDIR /workspace/builder

COPY go.mod go.mod
COPY go.sum go.sum

RUN go mod download

COPY builder-config.yaml builder-config.yaml

RUN go tool builder --config builder-config.yaml

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --chmod=555 --from=certs /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem /etc/ssl/certs/ca-certificates.crt

WORKDIR /

COPY --chmod=755 --from=builder /workspace/opentelemetry-collector/it-bench-otelcollector it-bench-otelcollector

ENTRYPOINT ["/it-bench-otelcollector"]

EXPOSE 4317 4318
