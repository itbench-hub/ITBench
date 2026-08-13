FROM registry.access.redhat.com/ubi10-minimal:10.2-1786398535@sha256:1e429ea364534f7baf494bac5cc54996b9b9d300f1da90e7b1dfa0ce455bfe39 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1786496329@sha256:1db86a2b0f77c1197b011de5140236effc27b1a1724c0105d4926857a0756de5 AS builder

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
