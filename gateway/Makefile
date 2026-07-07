.PHONY: build run test lint clean docker migrate-up migrate-down

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

migrate-up:
	go run ./cmd/migrate up

migrate-down:
	go run ./cmd/migrate down
