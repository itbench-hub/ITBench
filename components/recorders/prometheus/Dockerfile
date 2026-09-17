FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1789630856@sha256:c468f485f6bdc8ba6b106d63d4019851eaf1912182f7e67ff1a185234d58ebf7 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/prometheus-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --from=builder /build/prometheus-recorder /prometheus-recorder

ENTRYPOINT ["/prometheus-recorder"]
