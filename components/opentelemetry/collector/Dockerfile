FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:f0c7b9ae9914fcf183e7c36fc46864903c2d2caf3af327421913ae54b3d29e94 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1794184424@sha256:1e30f4a501268d9468011bf40d2a930c00a870f2fb6da6884118afd9cc5a6e7e AS builder

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

COPY --chmod=755 --from=builder /workspace/opentelemetry-collector/it-bench-otelcollector it-bench-otelcollector

ENTRYPOINT ["/it-bench-otelcollector"]

EXPOSE 4317 4318
