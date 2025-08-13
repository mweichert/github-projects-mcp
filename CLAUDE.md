This directory contains a fork of the `github-projects-mcp` repository. We are actively developing new features and tools for this Model Context Protocol (MCP) server that provides GitHub Projects integration.

## Development Process

Follow Test-Driven Development (TDD) when implementing new features:

1. **RED**: Write failing tests first that demonstrate the expected behavior
2. **GREEN**: Write minimal code to make tests pass
3. **REFACTOR**: Clean up and improve the code while keeping tests green

## Testing

Run tests using:
```bash
uv run pytest
```

For specific test files or methods:
```bash
uv run pytest test_file.py::TestClass::test_method -v
```
