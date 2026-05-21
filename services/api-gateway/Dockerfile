FROM golang:1.23-alpine AS builder

WORKDIR /app
COPY go.mod .
RUN go mod download
COPY main.go .
RUN CGO_ENABLED=0 go build -o api-gateway .

FROM alpine:3.20
WORKDIR /app
COPY --from=builder /app/api-gateway .
EXPOSE 8080
CMD ["./api-gateway"]
