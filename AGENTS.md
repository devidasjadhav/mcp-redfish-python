# AGENTS.md - Development Guidelines for Redfish MCP Project

## Build/Lint/Test Commands

### Testing
- Run all tests: `pytest`
- Run single test file: `pytest test_chatbot.py`
- Run specific test function: `pytest test_chatbot.py::test_function_name`

### Linting & Formatting
- Lint code: `flake8 .` (if installed)
- Format code: `black .` (if installed)
- Sort imports: `isort .` (if installed)
- Type check: `mypy .` (if installed)

## Code Style Guidelines

### Imports
- Standard library imports first
- Third-party imports second
- Local imports last
- One import per line
- Use absolute imports

### Naming Conventions
- Functions: `snake_case`
- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Classes: `PascalCase`

### Types & Documentation
- Use type hints for function parameters
- Include comprehensive docstrings with Args sections
- Document return types when non-obvious

### Error Handling
- Use try/except blocks for external operations (HTTP requests, file I/O)
- Catch specific exceptions where possible
- Return descriptive error messages as strings

### Code Structure
- Keep functions focused and under 50 lines
- Use descriptive variable names
- Prefer f-strings for string formatting
- Use meaningful constants for magic values

### HTTP & API Patterns
- Use requests library for HTTP operations
- Include proper headers (Content-Type: application/json)
- Handle HTTP status codes appropriately
- Validate JSON input/output</content>
<parameter name="filePath">/home/dev/workspace/mcp/test/AGENTS.md