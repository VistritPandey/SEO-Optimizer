FROM node:22-bookworm-slim
WORKDIR /opt/portfolio
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY verify.sh /opt/verify-portfolio.sh
RUN chmod 755 /opt/verify-portfolio.sh
