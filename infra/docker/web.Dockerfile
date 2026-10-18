FROM node:24-alpine
WORKDIR /repo
RUN corepack enable
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml turbo.json ./
COPY apps/api/package.json apps/api/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/config/package.json packages/config/package.json
COPY packages/shared/package.json packages/shared/package.json
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca NODE_USE_ENV_PROXY=1; fi; \
    pnpm install --frozen-lockfile
COPY . .
CMD ["pnpm", "--filter", "@sapsos/web", "dev"]
