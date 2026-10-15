# syntax=docker/dockerfile:1
# Multi-stage build for the Tezz POS web app (Next.js 14, App Router).

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* values are inlined into the client bundle at build time, so
# they must be exported as ENV *before* `npm run build` runs, not passed at
# container-run time (that would be a no-op for already-built client code).
ARG NEXT_PUBLIC_DEMO_API_KEY=""
ARG NEXT_PUBLIC_API_BASE="/api"
ENV NEXT_PUBLIC_DEMO_API_KEY=$NEXT_PUBLIC_DEMO_API_KEY
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

# `output: 'standalone'` (next.config.js) traces the minimal server + deps
# into .next/standalone; static assets still need to be copied alongside it.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
