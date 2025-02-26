import subprocess
import os
from typing import Optional

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

import logfire

logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_openai()

class CLIQuery(BaseModel):
    tool_name: str

ollama_model = OpenAIModel(model_name='llama3.2', base_url=os.getenv('OLLAMA_API_BASE'))
agent = Agent(
    deps_type=CLIQuery,
    model=ollama_model,
    retries=3,
)

@agent.tool
def get_help_text(ctx: RunContext[CLIQuery], cli_tool_name: str, subcommand: Optional[str] = None) -> str:
    """Gets help text for a tool or subcommand using the '-h' flag.

    Args:
        cli_tool_name: The name of the CLI tool.
        subcommand: The subcommand (optional).
    """
    try:
        command = [cli_tool_name]
        if subcommand:
            command.append(subcommand)
        command.append("-h")
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"

    except FileNotFoundError:
        return f"Error: Command '{cli_tool_name}' not found."

@agent.tool
def get_man_page(ctx: RunContext[CLIQuery], cli_tool_name: str) -> str:
    """Gets the man page for a tool.

    Args:
      tool_name: the name of the tool
    """
    try:
        command = ["man", cli_tool_name]
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error getting man page: {result.stderr}"

    except FileNotFoundError:
        return "Error: 'man' command not found.  Is it installed?"

@agent.system_prompt
def system_prompt(ctx: RunContext[CLIQuery]):
    return f"""
You are a CLI tool expert. You are tasked with explaining how to use a given command-line tool, based on a user's query.

You have access to the following tools:

- get_help_text:  Gets help text for a tool or subcommand using the '-h' flag.  This tool takes the tool name and an *optional* subcommand as arguments.
- get_man_page: Gets the man page for a tool. This tool takes the tool name.

Here's your strategy:

1. **Initial Help:** Start by getting the help text for the main tool (using `get_help_text` without a subcommand).
2. **Identify Subcommands:** Carefully examine the help text you receive. Look for sections describing subcommands.  These might be indicated by indentation, keywords like "Commands:", or a list of command names.
3. **Recursive Exploration:** For *each* potential subcommand you identify, call `get_help_text` *again*, this time passing the subcommand as an argument. This will give you the help text for that subcommand.
4. **Man Page (If Needed):** If `get_help_text` returns an error, or if the help text seems incomplete, use `get_man_page` to get more information about the main tool.
5. **Repeat:** Continue steps 2 and 3 recursively until you believe you have explored all subcommands (i.e., you no longer find new subcommands in the help text).
6. **Answer the Question:** Once you have gathered all the relevant help text (for the main tool and all subcommands), synthesize this information and provide a clear and concise answer to the user's original query. Include relevant examples from the help text where appropriate. Be as comprehensive as possible.
7. **Do not call a tool if it has already been called with the same inputs**

Users Query:
Tool: {ctx.deps.tool_name}
"""


def run_chat_interface(agent: Agent):
    console = Console()
    console.print(Panel("[bold]CLI Tool Explainer[/bold]", border_style="green"))

    while True:
        try:
            # First get the tool name
            tool_name = console.input("[bold]Enter the CLI tool name (or 'quit' to exit):[/bold] ")
            if tool_name.lower() == "quit":
                break

            console.print(f"\n[bold]Now asking questions about: {tool_name}[/bold]")
            
            prev_result = None
            
            # Inner loop for questions about the same tool
            while True:
                try:
                    query = console.input("\n[bold]Enter your question (or 'switch' to change tool, 'quit' to exit):[/bold] ")
                    
                    if query.lower() == "quit":
                        return  # Exit the entire program
                    if query.lower() == "switch":
                        break  # Break inner loop to switch tools

                    cli_query = CLIQuery(tool_name=tool_name)

                    with console.status("Thinking..."):
                        final_result = agent.run_sync(query, message_history=prev_result.new_messages() if prev_result else [], deps=cli_query)

                    # Store the Q&A in conversation history
                    prev_result = final_result
                    console.print(
                        Panel(Markdown(final_result.data), title="Explanation", border_style="blue")
                    )

                except KeyboardInterrupt:
                    console.print("\n[bold]Switching tools...[/bold]")
                    break

        except KeyboardInterrupt:
            console.print("\n[bold]Exiting...[/bold]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")


def main():
    """Main function to run the application."""
    run_chat_interface(agent)


if __name__ == "__main__":
    main()