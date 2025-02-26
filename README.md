# CLI Tool Explainer

A Python-based interactive CLI tool that helps users understand command-line tools by providing detailed explanations and exploring their subcommands.

## Features

- Interactive command-line interface
- Detailed explanations of CLI tools and their subcommands
- Support for help text and man pages

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cli_explain
```

2. Create and activate a virtual environment using uv:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install dependencies using uv:
```bash
uv install .
```

## Usage

Run the CLI explainer:
```bash
uv run cli_explainer.py
```

Once started:
1. Enter the name of the CLI tool you want to learn about
2. Ask questions about the tool's usage, options, or subcommands
3. Type 'switch' to change to a different tool
4. Type 'quit' to exit the program

## Example Session

```
CLI Tool Explainer

Enter the CLI tool name (or 'quit' to exit): git

Now asking questions about: git

Enter your question (or 'switch' to change tool, 'quit' to exit): How do I create a new branch?

[Explanation appears here]
```

## Environment Variables

- `OLLAMA_API_BASE`: Set this to your Ollama API endpoint if you're using a custom setup
