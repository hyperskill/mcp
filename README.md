# MCP-Hyperskill

<img src="http://nanda-registry.com/api/v1/verification/badge/a3e09952-e1bf-44ed-96cc-65defbf3d8d4/" alt="Verified MCP Server" />

A FastMCP integration with Hyperskill that allows AI agents to explain programming topics using Hyperskill's learning resources.

## Features

- Get explanations of code concepts with links to Hyperskill topics
- Search for programming topics on Hyperskill

## Installation

```bash
# Install dependencies using UV with pyproject.toml
uv sync
```

## Usage

To run the server:

```bash
uv run main.py
```

This will start a server on `http://0.0.0.0:8080` that AI agents can connect to.

### Command-line Arguments

The server supports the following command-line arguments:

```bash
uv run main.py [--host HOST] [--port PORT] [--debug]
```

- `--host HOST`: Host to bind the server to (default: 0.0.0.0)
- `--port PORT`: Port to bind the server to (default: 8080)
- `--debug`: Run in debug mode

Example:

```bash
uv run main.py --host 127.0.0.1 --port 9000 --debug
```

## MCP Tools

### explain_topics_in_the_code

Explains programming topics present in code by finding relevant Hyperskill resources.

Parameters:
- `topics`: List of key topics or concepts that need explanation
- `programming_language`: Programming language of the given code

### find_topics_on_hyperskill

Searches Hyperskill for specific programming topics.

Parameters:
- `topics`: List of topic keywords to search for
- `programming_language`: Programming language to filter topics by

## Example Usage

When interacting with an AI agent that has access to MCP-Hyperskill, you can ask:

```
Explain topics in the code using Hyperskill:


def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(result)
```

The AI agent will identify key concepts like "recursion", "functions", and "fibonacci sequence" and provide Hyperskill links for learning more about these topics.

The response will include:
- Topic titles
- Links to Hyperskill learning resources
- Topic hierarchies showing where these concepts fit in the curriculum

<div align="center">
  <img src="resources/cursor_example.webp" alt="Example of topic explanation in Cursor" width="600">
  <p><em>Example of AI explaining code topics with Hyperskill resources in Cursor</em></p>
</div>
