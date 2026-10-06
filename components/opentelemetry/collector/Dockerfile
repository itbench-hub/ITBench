FROM registry.access.redhat.com/ubi10-minimal:10.2-1791269426@sha256:843abc6aab53312a9e3fb5edccbdb15c84794fe41e7b01de7447329ac1e086ad AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1791216793@sha256:8106afc02bac6f3d78384a7380460aa51bf0118f8179453609c80ca1858c5454 AS builder

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
