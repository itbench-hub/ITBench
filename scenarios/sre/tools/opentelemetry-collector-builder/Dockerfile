FROM registry.access.redhat.com/ubi10-minimal:10.2-1786960640@sha256:61f820b7893b6226e499e928db99c59a0a9135aa17e4e056fdaf1015908cca14 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1786959166@sha256:26d2558491a2ec993c46fc13c68ebb7638737661825d9876b40311f5e585d7c2 AS builder

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
