FROM registry.access.redhat.com/ubi10/ubi-minimal:10.3-1795196920@sha256:d63890a635f8f19177bce1775f74f587a47f4456844f1392456c4e3673a48753 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.27.3-1795335720@sha256:1b1b6d0a428218c617c43629240c42954beff44c48d47fe2ed25f1dfdc9dfa54 AS builder

ENV CGO_ENABLED=0

WORKDIR /workspace/builder

COPY go.mod go.mod
COPY go.sum go.sum

RUN go mod download

COPY builder-config.yaml builder-config.yaml

RUN go tool builder --config builder-config.yaml

FROM gcr.io/distroless/static-debian13:nonroot@sha256:8ce6dd87e9823c5b48dcfb2c8604714ccb351ce59607327bcc4957448da279b5

COPY --chmod=555 --from=certs /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem /etc/ssl/certs/ca-certificates.crt

WORKDIR /

COPY --chmod=755 --from=builder /workspace/opentelemetry-collector/itbench-otelcollector itbench-otelcollector

ENTRYPOINT ["/itbench-otelcollector"]

EXPOSE 4317 4318
