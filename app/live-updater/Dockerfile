FROM golang:1.24 AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . . 

ENV CGO_ENABLED=0 GOOS=linux GOARCH=amd64

RUN go build -o main .

FROM alpine:latest

RUN apk --no-cache add ca-certificates
WORKDIR /app

COPY --from=builder /app/main .

ENTRYPOINT [ "./main" ]