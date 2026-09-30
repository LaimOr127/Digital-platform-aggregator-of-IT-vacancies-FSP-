# ---- build: node нужен только здесь, в итоговый образ не попадает ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY . .
# тесты — часть сборки: образ с непрошедшими тестами не собирается
RUN npm test && npm run build

# ---- runtime: тот же базовый образ caddy, что у proxy (общие слои) ----
FROM caddy:2-alpine AS runtime
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 8080
