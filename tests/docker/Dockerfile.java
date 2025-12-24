# Java language test - Shows what's needed for Java indexing

FROM cicada-base

# Install Java and Coursier
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

# Install Coursier
RUN curl -fL "https://github.com/coursier/coursier/releases/latest/download/cs-x86_64-pc-linux.gz" | gzip -d > /usr/local/bin/cs && \
    chmod +x /usr/local/bin/cs

# Copy test fixture
COPY tests/fixtures/sample_java /workspace/project

# Test indexing (uses coursier fallback in JVM indexer)
WORKDIR /workspace/project
RUN python -m cicada claude --fast && \
    echo "✅ Java indexing successful"
