# C/C++ language test - Shows what's needed for C/C++ indexing

FROM cicada-base

# Install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install scip-clang (need to download binary from GitHub releases)
RUN wget "https://github.com/sourcegraph/scip-clang/releases/download/v0.3.2/scip-clang-linux-amd64" \
    -O /usr/local/bin/scip-clang && \
    chmod +x /usr/local/bin/scip-clang

# Copy test fixtures (C and C++ share scip-clang)
COPY tests/fixtures/sample_c /workspace/project_c
COPY tests/fixtures/sample_cpp /workspace/project_cpp

# Test C indexing
WORKDIR /workspace/project_c
RUN python -m cicada claude --fast && \
    echo "✅ C indexing successful"

# Test C++ indexing
WORKDIR /workspace/project_cpp
RUN python -m cicada claude --fast && \
    echo "✅ C++ indexing successful"
