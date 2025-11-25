# --- Build Stage ---
FROM debian:bookworm-slim AS builder

ARG TARGETARCH
ARG LDC_VERSION="1.36.0"

WORKDIR /opt

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    xz-utils \
    build-essential \
    libxml2 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Download LDC based on architecture (amd64 vs arm64)
RUN if [ "$TARGETARCH" = "amd64" ]; then \
        LDC_ARCH="x86_64"; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
        LDC_ARCH="aarch64"; \
    else \
        echo "Unsupported architecture: $TARGETARCH"; exit 1; \
    fi && \
    curl -L -o ldc.tar.xz "https://github.com/ldc-developers/ldc/releases/download/v${LDC_VERSION}/ldc2-${LDC_VERSION}-linux-${LDC_ARCH}.tar.xz" && \
    tar -xf ldc.tar.xz && \
    mv "ldc2-${LDC_VERSION}-linux-${LDC_ARCH}" ldc && \
    rm ldc.tar.xz

ENV PATH="/opt/ldc/bin:${PATH}"

WORKDIR /app

# Copy source and build
COPY . .
RUN dub build --build=release --compiler=ldc2

# --- Runtime Stage ---
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy binary and assets
COPY --from=builder /app/reticulum /usr/local/bin/reticulum
COPY --from=builder /app/rules /app/rules

ENTRYPOINT ["reticulum"]
CMD ["--help"]