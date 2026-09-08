# Multi-stage build: compile the Vite/React app, then serve the static bundle
# with nginx. nginx also reverse-proxies /api/* to the backend so the frontend
# code can keep using plain relative fetch("/api/...") calls in every
# deployment target -- only BACKEND_INTERNAL_URL changes between them (compose
# service name vs. Railway's private-networking hostname).
FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV BACKEND_INTERNAL_URL=http://backend:8000
EXPOSE 80
