FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10-1792768404@sha256:557f358c83892a8b94fb72649a99e1c303a625d240547fb97a9cbc1620e808c0 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/prometheus-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:18f4cc26c9ffa7f20a359298be7deadac5c607c8e03a02b8119f1a5fc2f82c99

COPY --from=builder /build/prometheus-recorder /prometheus-recorder

ENTRYPOINT ["/prometheus-recorder"]
