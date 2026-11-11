FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:cc3d766e796fbb50d6fcd599f4bad4c231aeae41822c6e86e7da664a996221ca AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1794255104@sha256:e94c38ff4a099b755af60c73ac87198c613f369eb7f818d45c96fbc3f21047de AS builder

ENV CGO_ENABLED=0

WORKDIR /workspace/builder

COPY go.mod go.mod
COPY go.sum go.sum

RUN go mod download

COPY builder-config.yaml builder-config.yaml

RUN go tool builder --config builder-config.yaml

FROM gcr.io/distroless/static-debian13:nonroot@sha256:25ac8f0c3b2334a9eb05452266bd4697864a8c8ef0ef71e5e6480d7f92868329

COPY --chmod=555 --from=certs /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem /etc/ssl/certs/ca-certificates.crt

WORKDIR /

COPY --chmod=755 --from=builder /workspace/opentelemetry-collector/itbench-otelcollector itbench-otelcollector

ENTRYPOINT ["/itbench-otelcollector"]

EXPOSE 4317 4318
