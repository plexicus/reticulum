# --- Build Stage ---
FROM rust:1-slim-bookworm AS builder

WORKDIR /app

# Copy source and build
COPY Cargo.toml Cargo.lock* ./
COPY src ./src
RUN cargo build --release

# --- Runtime Stage ---
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy binary and assets
COPY --from=builder /app/target/release/reticulum /usr/local/bin/reticulum
COPY rules /app/rules

ENTRYPOINT ["reticulum"]
CMD ["--help"]
