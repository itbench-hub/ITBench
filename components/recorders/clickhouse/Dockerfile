FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1793908205@sha256:cb712e78c45e429142e846c1b8b91894970eab3b66fd5a95d336b65b4f7bb877 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/clickhouse-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:25ac8f0c3b2334a9eb05452266bd4697864a8c8ef0ef71e5e6480d7f92868329

COPY --from=builder /build/clickhouse-recorder /clickhouse-recorder

ENTRYPOINT ["/clickhouse-recorder"]
