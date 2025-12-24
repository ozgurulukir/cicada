# Dart language test - Shows what's needed for Dart indexing

FROM cicada-base

# Install Dart SDK
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    wget \
    && wget -qO- https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/dart.gpg \
    && echo 'deb [signed-by=/usr/share/keyrings/dart.gpg arch=amd64] https://storage.googleapis.com/download.dartlang.org/linux/debian stable main' | tee /etc/apt/sources.list.d/dart_stable.list \
    && apt-get update && apt-get install -y dart \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/lib/dart/bin:$PATH"
ENV PATH="/root/.pub-cache/bin:$PATH"

# Install scip_dart
RUN dart pub global activate scip

# Copy test fixture
COPY tests/fixtures/sample_dart /workspace/project

# Test indexing (auto-runs dart pub get)
WORKDIR /workspace/project
RUN python -m cicada claude --fast && \
    echo "✅ Dart indexing successful"
