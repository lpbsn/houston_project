# -----------------------------------------------------------------------------
# Stage 1: production build
# -----------------------------------------------------------------------------
FROM node:24-alpine AS build

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json* apps/web/
COPY contracts/ contracts/
COPY apps/web/ apps/web/

WORKDIR /app/apps/web

RUN npm ci && npm run build

# -----------------------------------------------------------------------------
# Stage 2: local dev (docker-compose.yml target: development)
# -----------------------------------------------------------------------------
FROM node:24-alpine AS development

WORKDIR /app/apps/web

COPY apps/web/package.json apps/web/package-lock.json* ./

RUN npm ci

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# -----------------------------------------------------------------------------
# Stage 3: production static serve (default final stage + prod-test)
# -----------------------------------------------------------------------------
FROM nginx:1.27-alpine AS production

COPY infra/docker/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
