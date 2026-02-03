# =============================================================================
# AWS Comparator - Multi-stage Docker Build
# =============================================================================
# This Dockerfile creates a minimal Alpine-based image for running aws-comparator
# without requiring Python or any dependencies to be installed on the host.
#
# Build: docker build -t aws-comparator .
# Run:   docker run --rm -v ~/.aws:/home/appuser/.aws:ro aws-comparator --help
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
# Install build dependencies and create a virtual environment with the package
# installed. This stage is discarded in the final image.
# -----------------------------------------------------------------------------
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies required for compiling Python packages
# - gcc, musl-dev: C compiler and standard library headers
# - libffi-dev: Foreign Function Interface library (needed by some dependencies)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev

# Copy only the files needed for installation
# This ordering maximizes Docker layer caching
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Create virtual environment and install the package
# Using a venv allows us to copy just the installed packages to the runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install the package with no cache to minimize size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Remove unnecessary files to reduce size
RUN find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyo" -delete 2>/dev/null || true && \
    find /opt/venv -type f -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /opt/venv/lib/python*/site-packages/pip* 2>/dev/null || true && \
    rm -rf /opt/venv/lib/python*/site-packages/setuptools* 2>/dev/null || true && \
    rm -rf /opt/venv/lib/python*/site-packages/wheel* 2>/dev/null || true && \
    rm -rf /opt/venv/lib/python*/site-packages/botocore/data/*/2*/examples* 2>/dev/null || true

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
# Minimal runtime image with only the necessary components to run aws-comparator
# -----------------------------------------------------------------------------
FROM python:3.11-alpine AS runtime

# Add labels for better image documentation
LABEL maintainer="AWS Comparator Team"
LABEL description="AWS Account Comparator - Compare AWS resources across accounts"
LABEL version="0.1.0"

WORKDIR /app

# Copy the virtual environment from the builder stage
# This contains all installed packages without build dependencies
COPY --from=builder /opt/venv /opt/venv

# Set the virtual environment path
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables for better container behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user for security
# Using UID 1000 for compatibility with most host systems
RUN adduser -D -u 1000 appuser

# Create .aws directory for mounted credentials (optional)
RUN mkdir -p /home/appuser/.aws && \
    chown -R appuser:appuser /home/appuser/.aws

# Switch to non-root user
USER appuser

# Set the entrypoint to aws-comparator
# Users can pass any CLI arguments after the image name
ENTRYPOINT ["aws-comparator"]

# Default command shows help
CMD ["--help"]
