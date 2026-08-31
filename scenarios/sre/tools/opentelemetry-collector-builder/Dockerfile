FROM registry.access.redhat.com/ubi10-minimal:10.2-1788137716@sha256:d801168f5e8b108586c27a4fd5c92e3c1e8d061084383713926e2ca61b8b6c64 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1787080020@sha256:a7e505b797c95c8e618a364de3a8c0383882935a12a1222a376d667c65d119b8 AS builder

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
