FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:9712ae522acef7e90c571280b4faf69614b59395448d6bfb1c780c3bbf168218 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1791865085@sha256:dc8fa0b4f60cdb933ffb269ef4ca7212ae4b4ba6f8747b23cf0f48d0458564a5 AS builder

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
