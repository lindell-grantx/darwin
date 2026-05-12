FROM node:24-slim

WORKDIR /app/server

COPY server/package.json server/package-lock.json ./
RUN npm ci

COPY server/ .

EXPOSE 3300
CMD ["node", "src/server.ts"]
