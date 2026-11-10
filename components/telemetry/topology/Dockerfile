FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1794255104@sha256:e94c38ff4a099b755af60c73ac87198c613f369eb7f818d45c96fbc3f21047de AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/topology-writer ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:25ac8f0c3b2334a9eb05452266bd4697864a8c8ef0ef71e5e6480d7f92868329

COPY --from=builder /build/topology-writer /topology-writer

ENTRYPOINT ["/topology-writer"]
