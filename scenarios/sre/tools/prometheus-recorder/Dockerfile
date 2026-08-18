FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1786959166@sha256:26d2558491a2ec993c46fc13c68ebb7638737661825d9876b40311f5e585d7c2 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/prometheus-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:f7f8f729987ad0fdf6b05eeeae94b26e6a0f613bdf46feea7fc40f7bd72953e6

COPY --from=builder /build/prometheus-recorder /prometheus-recorder

USER nonroot:nonroot

ENTRYPOINT ["/prometheus-recorder"]
