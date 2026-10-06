FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1791275880@sha256:d517b3c1043131d6d3cfa341beac96300302d9149504e452289d0bd904f5c3ab AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/clickhouse-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --from=builder /build/clickhouse-recorder /clickhouse-recorder

ENTRYPOINT ["/clickhouse-recorder"]
