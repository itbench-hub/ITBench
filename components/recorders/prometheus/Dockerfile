FROM registry.access.redhat.com/ubi10/go-toolset:1.27.4-1795471060@sha256:2067cf54243dbc9fe0c017c531e31ddd191af203f930fc7fce59ab2b8bb85449 AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /build/prometheus-recorder ./cmd/

FROM gcr.io/distroless/static-debian13:nonroot@sha256:8ce6dd87e9823c5b48dcfb2c8604714ccb351ce59607327bcc4957448da279b5

COPY --from=builder /build/prometheus-recorder /prometheus-recorder

ENTRYPOINT ["/prometheus-recorder"]
