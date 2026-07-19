# Build Flutter Web assets.
FROM ghcr.io/cirruslabs/flutter:3.24.5 AS builder

WORKDIR /app

COPY pubspec.yaml ./
RUN flutter pub get

COPY . .

ARG APP_ENV=prod
ARG BASE_URL=https://mkc.example.com/api/v1
ARG STORAGE_HOST=mkc.example.com

RUN flutter build web \
    --release \
    --dart-define=APP_ENV=${APP_ENV} \
    --dart-define=BASE_URL=${BASE_URL} \
    --dart-define=STORAGE_HOST=${STORAGE_HOST}

# Serve static assets.
FROM nginx:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/build/web /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
