FROM registry.access.redhat.com/ubi10/go-toolset:1.26.5-1786496329@sha256:1db86a2b0f77c1197b011de5140236effc27b1a1724c0105d4926857a0756de5 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/clickhouse-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:f7f8f729987ad0fdf6b05eeeae94b26e6a0f613bdf46feea7fc40f7bd72953e6

COPY --from=builder /build/clickhouse-recorder /clickhouse-recorder

USER nonroot:nonroot

ENTRYPOINT ["/clickhouse-recorder"]
