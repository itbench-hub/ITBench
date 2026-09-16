FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1788946935@sha256:de00e16138966f9fed6bca2d22d28f6cc0d50b26ef6977398e2d8980d80be75f AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/jaeger-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --from=builder /build/jaeger-recorder /jaeger-recorder

ENTRYPOINT ["/jaeger-recorder"]
