FROM registry.access.redhat.com/ubi10/go-toolset:1.27.3-1795335720@sha256:1b1b6d0a428218c617c43629240c42954beff44c48d47fe2ed25f1dfdc9dfa54 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/topology-writer ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:8ce6dd87e9823c5b48dcfb2c8604714ccb351ce59607327bcc4957448da279b5

COPY --from=builder /build/topology-writer /topology-writer

ENTRYPOINT ["/topology-writer"]
