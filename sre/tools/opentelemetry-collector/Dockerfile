FROM registry.access.redhat.com/ubi10-minimal:10.0-1758699349 AS certs

FROM registry.access.redhat.com/ubi10/go-toolset:1.24.6-1760919472 AS builder

WORKDIR /workspace

COPY go.mod go.mod
COPY go.sum go.sum

RUN go mod download

COPY manafest.yaml manafest.yaml

RUN go tool builder --config manafest.yaml

FROM gcr.io/distroless/static-debian12:nonroot

COPY --from=certs /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem /etc/ssl/certs/ca-certificates.crt

COPY --from=builder /workspace/out/it-bench-otelcollector it-bench-otelcollector

ENTRYPOINT ["./it-bench-otelcollector"]

EXPOSE 4317 4318
