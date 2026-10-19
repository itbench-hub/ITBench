FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1792406018@sha256:78049192391115cdcc3a794bf0e7295a1f54fbb110c0a832e6b1254dbd15239d AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/topology-writer ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --from=builder /build/topology-writer /topology-writer

ENTRYPOINT ["/topology-writer"]
