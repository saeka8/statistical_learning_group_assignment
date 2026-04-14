# ---- Dependencies ----
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# ---- Dev server ----
FROM deps AS dev

COPY . .
EXPOSE 5173
CMD ["node", "./node_modules/vite/bin/vite.js", "--configLoader", "native", "-c", "vite.config.mjs", "--host"]

# ---- Build ----
FROM deps AS build

COPY . .
RUN npm run build

# ---- Serve (production) ----
FROM nginx:alpine AS serve

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
