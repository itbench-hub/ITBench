FROM registry.access.redhat.com/ubi10-minimal:10.2-1791444377@sha256:bcecd3e74c9d03eb1a596c6c8f366775a289d422ac5925ec1539924d762ebf23 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1791462472@sha256:7ec4dc8858bd3467b5e13ecccc9f913a0908978e50420958922d4494bf7b65b9 AS builder

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
