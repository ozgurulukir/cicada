# Go language test - Shows what's needed for Go indexing

FROM cicada-base

# Install Go
RUN apt-get update && apt-get install -y \
    golang-go \
    && rm -rf /var/lib/apt/lists/*

# Install scip-go
ENV GOPATH=/root/go
ENV PATH=$PATH:/root/go/bin
RUN go install github.com/sourcegraph/scip-go@latest

# Copy test fixture
COPY tests/fixtures/sample_go /workspace/project

# Test indexing
WORKDIR /workspace/project
RUN python -m cicada claude --fast && \
    echo "✅ Go indexing successful"
