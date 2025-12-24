# SCIP Language E2E Docker Tests

This directory contains end-to-end tests for all SCIP languages in clean Docker environments.

## Test Philosophy

These tests are designed to:
1. **Start from a clean slate** - Base image with only Cicada and git
2. **Copy a real project** - Use our fixture projects
3. **Try to index** - Run `cicada claude --fast`
4. **Document what fails** - Capture missing dependencies

## Quick Start

### Test All Languages

```bash
./test-all-languages.sh
```

### Test Single Language

```bash
./test-single-language.sh go
./test-single-language.sh java
# etc.
```

## Test Structure

### Base Image (`Dockerfile.base`)

Minimal environment:
- Python 3.11
- Git (required by Cicada)
- uv (for installing Cicada)
- Cicada installed from source

**Does NOT include:**
- Language runtimes (Go, Java, Ruby, etc.)
- SCIP indexers (scip-go, scip-java, etc.)
- Build tools (sbt, gradle, etc.)

### Per-Language Tests

Each language test:
1. Uses the base image
2. Mounts the fixture directory as read-only
3. Tries to run `python -m cicada claude --fast`
4. Captures output to `/tmp/cicada-test-{language}.log`

## Expected Failures

In the base environment, **all languages should fail** because:

### Go
- Missing: `scip-go` binary
- Error: `[Errno 2] No such file or directory: 'scip-go'`

### Java
- Missing: `coursier` or `scip-java`
- Error: `scip-java not found. Install via: brew install coursier/formulas/coursier`

### Scala
- Missing: `sbt`, `coursier`
- Error: Same as Java + sbt version issues

### Ruby
- Missing: `scip-ruby` binary
- Error: `[Errno 2] No such file or directory: 'scip-ruby'`

### Dart
- Missing: `dart` SDK, `scip_dart`
- Error: `dart command not found. Install Dart SDK: https://dart.dev/get-dart`

### C/C++
- Missing: `scip-clang` binary
- Error: `[Errno 2] No such file or directory: 'scip-clang'`

### C#/VB
- Missing: `.NET SDK`, `scip-dotnet`
- Error: `[Errno 2] No such file or directory: 'scip-dotnet'`

## What We Learn

These tests expose:
1. **Missing tool detection** - Are our error messages helpful?
2. **Installation instructions** - Do we guide users to the right place?
3. **Dependency chains** - What tools depend on what?
4. **Auto-setup limits** - What can we auto-install vs. what needs docs?

## Future: Per-Language Dockerfiles

Each language should have a `Dockerfile.{language}` that:
```dockerfile
FROM cicada-base

# Install language runtime
RUN apt-get update && apt-get install -y golang-go

# Install SCIP indexer
RUN go install github.com/sourcegraph/scip-go@latest

# Test
COPY tests/fixtures/sample_go /workspace/project
RUN cd /workspace/project && python -m cicada claude --fast
```

This documents the **minimum required setup** for each language.

## Running Tests

### Prerequisites
- Docker installed and running
- From cicada repo root

### Commands

```bash
cd tests/docker

# Test all (expect failures)
./test-all-languages.sh

# Test one language
./test-single-language.sh go

# View detailed logs
cat /tmp/cicada-test-sample_go.log
```

## Success Criteria

A test "passes" when:
1. ✅ Clear error message about missing tool
2. ✅ Helpful installation instructions
3. ✅ No confusing stack traces

A test "fails" when:
1. ❌ Cryptic error message
2. ❌ No guidance on what to install
3. ❌ Stack trace without context
