FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:c3fe95ec9f53a3888c47314eb4d08bde09ebde646a428137b445091afe1daf89 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1793908205@sha256:cb712e78c45e429142e846c1b8b91894970eab3b66fd5a95d336b65b4f7bb877 AS builder

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
