FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1787080020@sha256:a7e505b797c95c8e618a364de3a8c0383882935a12a1222a376d667c65d119b8 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/clickhouse-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:1c2c046bc09ed40fad370b599a0b1ae7987f55b01e247cf27a7c27cd97e5bbc7

COPY --from=builder /build/clickhouse-recorder /clickhouse-recorder

USER nonroot:nonroot

ENTRYPOINT ["/clickhouse-recorder"]
