# Cicada Feature Reference

**CICADA** - Code Intelligence: Contextual Analysis, Discovery, and Attribution

## Language Support
1. Elixir Support - Full AST-level indexing with module, function, and macro extraction
2. Python Support - SCIP-based indexing with class and method detection
3. Erlang Support - Beta support for Erlang codebases
4. TypeScript Support - Experimental support via SCIP

## Code Indexing
1. AST-Level Indexing - Extracts module, function, and class definitions with signatures and specs
2. Incremental Indexing - Only reindexes changed files for fast updates
3. Automatic Language Detection - Detects project type from mix.exs or pyproject.toml
4. Watch Mode - Automatically reindexes files when changes are detected
5. Configurable Keyword Tiers - Fast, Regular, or Max tiers for keyword extraction quality
6. String-Based Indexing - Indexes string literals from function bodies (SQL, error messages, etc.)

## Semantic Search
1. Keyword Search - Find code by concept using KeyBERT-based semantic matching
2. Pattern Search - Find code using wildcards (*) and OR patterns (|)
3. Mixed Queries - Combine keywords and patterns in a single search
4. Match Source Filtering - Search in docs, strings, or comments separately
5. Scope Filtering - Filter by public/private visibility
6. Path Filtering - Filter results by file path using glob patterns
7. Recent Changes Filter - Filter to code changed in the last 14 days

## Module Analysis
1. Complete API View - View all functions with arity, signatures, docs, and typespecs
2. What Calls It - See all modules and functions that depend on a module
3. What It Calls - See all dependencies a module imports, aliases, or uses
4. Transitive Dependencies - Explore dependencies at configurable depth levels
5. Wildcard Module Search - Search modules using patterns like `MyApp.*`
6. Python Class Display - View classes with method counts and signatures

## Function Analysis
1. Function Definition Search - Find function definitions by name or pattern
2. Call Site Tracking - See all locations where a function is called
3. Usage Examples - Get actual code snippets showing how functions are used
4. Bidirectional Analysis - See both callers and callees for any function
5. Arity Filtering - Filter functions by specific arity
6. Changed Since Filter - Filter functions changed after a specific date

## Git History & Attribution
1. Line Blame - Find who wrote a specific line and in which PR
2. Range Blame - Group consecutive lines by authorship with PR enrichment
3. Function Evolution - Track how a function has changed over time
4. File PR History - View all PRs that modified a file
5. Author Filtering - Filter history by author name
6. Time Filtering - View recent, older, or all-time history

## PR Indexing
1. PR Index - Index GitHub pull requests for offline lookup
2. PR Descriptions - Access PR descriptions and commit messages
3. Review Comments - Access PR review comments and discussions
4. Incremental PR Updates - Only fetch new PRs since last index

## Co-Change Analysis
1. Co-Change Detection - Identify files frequently modified together
2. Function Co-Change - Identify functions that change together
3. Search Score Boosting - Boost search results based on co-change relationships
4. Adaptive Commit Analysis - Automatically adjusts analysis depth by repo size

## Editor Integration
1. Claude Code Setup - One-command setup for Claude Code editor
2. Cursor Setup - One-command setup for Cursor editor
3. VS Code Setup - One-command setup for VS Code editor
4. Gemini CLI Setup - One-command setup for Gemini CLI
5. Codex Setup - One-command setup for Codex editor
6. Zed Setup - One-command setup for Zed editor
7. MCP Server - Model Context Protocol server for AI assistants

## CLI Tools
1. Interactive Setup - `cicada install` with editor and model selection
2. Index Command - Index projects with customizable options
3. Watch Command - Monitor files and auto-reindex on changes
4. Status Command - Display index health, links, and configurations
5. Stats Command - View usage statistics, tool calls, and token metrics
6. Link Command - Share indexes across repositories or worktrees
7. Clean Command - Remove Cicada configuration and indexes
8. Run Command - Execute MCP tools directly from command line
9. Serve Command - Start REST API server for HTTP access to tools

## MCP Tools
1. query - Smart code discovery with keyword/pattern auto-detection
2. search_module - View complete module API with dependency analysis
3. search_function - Find function definitions and all call sites
4. git_history - Unified tool for all git history queries
5. expand_result - Drill down into query results for complete details
6. refresh_index - Force refresh the index to pick up recent changes
7. query_jq - Execute custom jq queries against the index

## Output & Token Optimization
1. Compact Output - Token-efficient responses with essential info only
2. Verbose Mode - Enable full documentation, specs, and examples
3. Code Snippets - Optional code context around results
4. Pagination - Limit and offset for large result sets
5. Automatic Truncation - Large results are automatically truncated

## Advanced Features
1. jq Query Support - Execute arbitrary jq queries against the index
2. Schema Discovery - Discover available index fields with `| schema`
3. Sample Mode - Preview large datasets with automatic limiting
4. Repository Linking - Link repositories to share indexes
5. Co-occurrence Keywords - Intelligent keyword suggestions based on patterns
6. REST API Server - HTTP access to all MCP tools with OpenAPI docs
