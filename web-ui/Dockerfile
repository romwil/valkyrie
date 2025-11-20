# Multi-stage Dockerfile for Valkyrie Web UI

# Stage 1: Builder
FROM node:18-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY web-ui/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY web-ui/ .

# Build the application
RUN npm run build

# Stage 2: Production with nginx
FROM nginx:alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/*

# Copy custom nginx config
COPY web-ui/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user
RUN adduser -D -u 1000 valkyrie && \
    chown -R valkyrie:valkyrie /usr/share/nginx/html && \
    chown -R valkyrie:valkyrie /var/cache/nginx && \
    chown -R valkyrie:valkyrie /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R valkyrie:valkyrie /var/run/nginx.pid

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Switch to non-root user
USER valkyrie

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
