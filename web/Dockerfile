# syntax=docker/dockerfile:1.7
#
# Ragent Web (Next.js BFF) image.
#
# Three-stage build:
#   * deps   installs all dependencies (incl. devDependencies — the
#            Next.js / Tailwind / TS toolchain only runs at build
#            time, so they must be present in the build stage's
#            node_modules but are NOT shipped to the runtime image).
#   * build  runs `next build`, which produces `.next/standalone`
#            (self-contained server.js + pruned node_modules) thanks
#            to `output: "standalone"` in next.config.ts.
#   * runtime is a clean node:22-alpine layer with only the
#            standalone bundle + static assets + public/ — no source,
#            no dev tooling, no full node_modules.

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=6 \
    CMD wget -qO- http://127.0.0.1:3000/api/auth/session >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
