FROM registry.access.redhat.com/ubi10-minimal:10.2-1785332632@sha256:ceaad73890ea88685eeb1b40a502b7983f2cfac6f1aa10915d1176d51eb90124 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1785776111@sha256:d3e72ee5779487d235416ccbc3c8a656889d63de9279be9ba17ecfe1abd01d6c AS builder

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
