FROM registry.access.redhat.com/ubi10/go-toolset:1.27.3-1793903644@sha256:05f3da136a4dbe077f30606e2e53a4f5cab185989c98309823ea06a9a1c52a50 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/clickhouse-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:8ce6dd87e9823c5b48dcfb2c8604714ccb351ce59607327bcc4957448da279b5

COPY --from=builder /build/clickhouse-recorder /clickhouse-recorder

ENTRYPOINT ["/clickhouse-recorder"]
