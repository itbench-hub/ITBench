FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1793622842@sha256:05619897582acb01ee5dd3eaa2934a7cc2f24409a255142a704b734ef07b68a6 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/prometheus-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:25ac8f0c3b2334a9eb05452266bd4697864a8c8ef0ef71e5e6480d7f92868329

COPY --from=builder /build/prometheus-recorder /prometheus-recorder

ENTRYPOINT ["/prometheus-recorder"]
