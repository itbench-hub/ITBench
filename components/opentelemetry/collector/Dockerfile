FROM registry.access.redhat.com/ubi10-minimal:10.2-1789645153@sha256:04febb4a74cc9ef3eca05ef851d92957276cc6e82fe8cb1ee44abf5114d440d8 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1789630856@sha256:c468f485f6bdc8ba6b106d63d4019851eaf1912182f7e67ff1a185234d58ebf7 AS builder

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
