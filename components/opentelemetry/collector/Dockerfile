FROM registry.access.redhat.com/ubi10-minimal:10.2-1790075626@sha256:e3a5632d7ae8a97e06f634522d06187f12793e90ac0d7b51bc671c83a96d8eda AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1789986821@sha256:5b963df4afc1fe44e33e524450c98eb20b12e4a3c00120dcc66afcac2309652b AS builder

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
