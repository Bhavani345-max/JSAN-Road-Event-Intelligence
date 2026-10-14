# REI web app. Build with frontend/ as the context:
#   docker build frontend
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules node_modules
COPY . .
# The /api proxy target is fixed when the app is built.
ARG API_BASE_URL=http://api:8000
ENV API_BASE_URL=$API_BASE_URL
RUN npm run build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
USER node
EXPOSE 3000
CMD ["npx", "next", "start"]
