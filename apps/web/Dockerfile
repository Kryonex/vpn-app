FROM node:20-alpine

WORKDIR /workspace/apps/web

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install

COPY apps/web /workspace/apps/web

EXPOSE 5173
