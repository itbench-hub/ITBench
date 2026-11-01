FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1793232609@sha256:5d2ab83e88506afee6bcc909fdab425ab979725ab30d6ad43a02aaa77e2258ff AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/clickhouse-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:25ac8f0c3b2334a9eb05452266bd4697864a8c8ef0ef71e5e6480d7f92868329

COPY --from=builder /build/clickhouse-recorder /clickhouse-recorder

ENTRYPOINT ["/clickhouse-recorder"]
