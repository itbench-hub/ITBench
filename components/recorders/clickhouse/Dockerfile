FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1791216793@sha256:8106afc02bac6f3d78384a7380460aa51bf0118f8179453609c80ca1858c5454 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/clickhouse-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --from=builder /build/clickhouse-recorder /clickhouse-recorder

ENTRYPOINT ["/clickhouse-recorder"]
