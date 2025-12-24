# Ruby language test - Shows what's needed for Ruby indexing

FROM cicada-base

# Install Ruby
RUN apt-get update && apt-get install -y \
    ruby \
    ruby-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install scip-ruby (need to download binary from GitHub releases)
RUN curl -L "https://github.com/sourcegraph/scip-ruby/releases/download/v0.4.7/scip-ruby-linux-amd64" \
    -o /usr/local/bin/scip-ruby && \
    chmod +x /usr/local/bin/scip-ruby

# Copy test fixture
COPY tests/fixtures/sample_ruby /workspace/project

# Test indexing
WORKDIR /workspace/project
RUN python -m cicada claude --fast && \
    echo "✅ Ruby indexing successful"
