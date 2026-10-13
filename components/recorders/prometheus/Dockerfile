FROM registry.access.redhat.com/ubi10/go-toolset:1.26.7-1791865085@sha256:dc8fa0b4f60cdb933ffb269ef4ca7212ae4b4ba6f8747b23cf0f48d0458564a5 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/prometheus-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3

COPY --from=builder /build/prometheus-recorder /prometheus-recorder

ENTRYPOINT ["/prometheus-recorder"]
