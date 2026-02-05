FROM registry.access.redhat.com/ubi10-minimal:10.1-1769677092 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.25.5-1770279878 AS builder

ENV CGO_ENABLED=0

WORKDIR /workspace/builder

COPY go.mod go.mod
COPY go.sum go.sum

RUN go mod download

COPY manafest.yaml manafest.yaml

RUN go tool builder --config manafest.yaml

FROM gcr.io/distroless/static-debian13:nonroot

COPY --chmod=555 --from=certs /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem /etc/ssl/certs/ca-certificates.crt

WORKDIR /

COPY --chmod=755 --from=builder /workspace/opentelemetry-collector/it-bench-otelcollector it-bench-otelcollector

ENTRYPOINT ["/it-bench-otelcollector"]

EXPOSE 4317 4318
