FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1791911662@sha256:4240036fd19bdad5d72ad15062d80b71cac9bc6b7789a45e53d6cc3e43167165 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/topology-writer ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --from=builder /build/topology-writer /topology-writer

ENTRYPOINT ["/topology-writer"]
