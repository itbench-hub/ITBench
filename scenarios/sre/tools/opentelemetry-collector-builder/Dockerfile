FROM registry.access.redhat.com/ubi10-minimal:10.2-1785778687@sha256:f0ed153f25c9a3df530ccf2c49ec04430efef206083cbbc16ca76a866ef096b5 AS certs

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
