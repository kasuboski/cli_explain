import os
import subprocess
import typer
from typing import Optional
from pydantic_ai import Agent, capture_run_messages, UnexpectedModelBehavior
from pydantic_ai.models.openai import OpenAIModel

system_prompt = """
You are a specialized CLI documentation assistant. Your primary role is to help users understand and use command-line tools effectively.

Core Responsibilities:
1. Analyze CLI tool documentation using the get_cli_help tool and get_manpage tool
2. For each discovered command, retrieve its specific help text
3. Provide accurate, focused answers based solely on the retrieved documentation
4. Format responses in a clear, user-friendly manner

Guidelines:
- Only use information from the tool's help text and commands
- Do not rely on prior knowledge
- If a specific tool isn't mentioned, infer it from context
- Always cite the specific help text or command documentation used

Response Format:
1. Brief overview of the command/tool
2. Detailed usage instructions
3. Relevant options and arguments
4. Examples when available
5. Source citation

Example Query: "What is command my_command?"

tool_response:
    my_command is a command that does something.
    Usage: my_command [options] [arguments]
    Options:
    -h, --help    Show this message and exit.
    -v, --verbose Verbose output.
    -q, --quiet   Quiet output.

Example Response:
Based on the my_command help documentation:

my_command is a utility that does something specific. Here's how to use it:

Usage:
  my_command [options] [arguments]

Available Options:
- -h, --help: Display help information
- -v, --verbose: Enable detailed output
- -q, --quiet: Suppress output messages

Source: my_command help text (via get_cli_help)
"""

ollama_model = OpenAIModel(model_name='llama3.2', base_url=os.getenv('OLLAMA_API_BASE'))
agent = Agent(ollama_model, deps_type=str, system_prompt=system_prompt)

# Tool to call a CLI with a configurable command and -h or --help
@agent.tool_plain
def get_cli_help(cli_tool_name: str, command: str = '') -> str:
    """
    Get the help text for a CLI tool.
    args:
        cli_tool_name: The name of the CLI tool to get help text for.
        command: The command to get help text for. If not provided, gets help text for the tool itself.
    """
    try:
        output = subprocess.run([cli_tool_name] + command.split() + ['-h'], capture_output=True, check=False, text=True)
        return output.stdout
    except FileNotFoundError:
        return f"{cli_tool_name} is not installed."
    except subprocess.CalledProcessError as e:
        # probably unreachable with check=False
        return f"Failed to get help text for {cli_tool_name}: {e}"

# Tool to search manpages for a tool
@agent.tool_plain
def get_manpage(cli_tool_name: str) -> str:
    """
    Get the manpage for a CLI tool.
    args:
        cli_tool_name: The name of the CLI tool to search a man page for.
    """
    try:
        output = subprocess.check_output(['man', cli_tool_name], text=True)
        return output
    except FileNotFoundError:
        return f"Manpage for {cli_tool_name} not found."
    except subprocess.CalledProcessError as e:
        return f"Failed to get manpage for {cli_tool_name}: {e}"

app = typer.Typer()

@app.command()
def chat(initial_question: Optional[str] = typer.Argument(None, help="Initial question to start the chat with")):
    """
    Start an interactive chat session to ask questions about CLI tools.
    """
    
    if initial_question:
        with capture_run_messages() as messages:
            try:
                result = agent.run_sync(initial_question)
                typer.echo(f"\nAnswer: {result.data}\n")
            except UnexpectedModelBehavior as e:
                typer.echo(f'An error occurred: {e}:{messages}', err=True)
                return

    while True:
        try:
            question = typer.prompt("\nAsk a question about any CLI tool (or 'exit' to quit)")
            
            if question.lower() in ['exit', 'quit', 'q']:
                typer.echo("Goodbye!")
                break

            with capture_run_messages() as messages:
                try:
                    result = agent.run_sync(question)
                    typer.echo(f"\nAnswer: {result.data}")
                except UnexpectedModelBehavior as e:
                    typer.echo(f'An error occurred: {e}:{messages}', err=True)

        except KeyboardInterrupt:
            typer.echo("\nGoodbye!")
            break

if __name__ == "__main__":
    app()
