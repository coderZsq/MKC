.PHONY: build run test lint clean docker

build:
	go build -o bin/server ./cmd/server

run:
	go run ./cmd/server

test:
	go test -race -coverprofile=coverage.out ./...

lint:
	golangci-lint run ./...

clean:
	rm -rf bin/ coverage.out

docker:
	docker build -t mkc-gateway:latest .
