**Project Goal:** Create a chat-based application that can explain how to use a given CLI tool, including its subcommands, by intelligently fetching help text and man pages. The LLM should be responsible for identifying subcommands and recursively calling tools.

**Overall Application Structure:**

The application will consist of:

1.  **Pydantic Models:** Define the structure of the data used within the agent (e.g., tool name, subcommand, help text).
2.  **Tools:** Implement functions that the agent can call (get help text via `-h`, get man page).  These functions should be simple and take basic string arguments.
3.  **Agent:** The core logic that decides which tools to use and processes the information. The system prompt will guide the agent's recursive exploration of subcommands.
4.  **Chat Interface:** A `rich`-based loop that takes user input, interacts with the agent, and displays the output.
5.  **Main Function:** A main function to set everything up and start the chat interface.

**Tasks:**

**Task 1: Project Setup and Pydantic Model Definition**

*   **Files Involved:** `cli_explainer.py`
*   **Description:**
    *   Set up the project: Create a new Python file (`cli_explainer.py`).
    *   Import necessary libraries: `pydantic`, `pydantic_ai`, `rich`, `subprocess`, `typing`.
    *   Define Pydantic models:
        *   `CLIQuery`: Stores the CLI query. Fields: `tool_name` (str), `query` (str).  This is used as the `deps_type` for the agent.
*   **Example Code Snippet (within `cli_explainer.py`):**

```python
from pydantic import BaseModel

class CLIQuery(BaseModel):
    tool_name: str
    query: str
```

**Task 2: Implement the `-h` Tool**

*   **Files Involved:** `cli_explainer.py`
*   **Description:**
    *   Create a function `get_help_text(tool_name: str, subcommand: Optional[str] = None) -> str` that:
        *   Takes the `tool_name` (str) and an *optional* `subcommand` (str) as input.  This is a key change: the LLM will directly provide the subcommand.
        *   Constructs the command to run (e.g., `tool_name -h` or `tool_name subcommand -h`).
        *   Uses `subprocess.run` to execute the command, capturing `stdout` and `stderr`.  Use `check=False` and check the return code.
        *   Returns the captured output (stdout) as a string. If there's an error, return an error message string (including stderr).
        *   Handles potential `FileNotFoundError` gracefully.
        *   Include a clear docstring explaining the function's purpose and arguments.
*    **Example Code Snippet:**

```python
import subprocess
from typing import Optional

def get_help_text(tool_name: str, subcommand: Optional[str] = None) -> str:
    """Gets help text for a tool or subcommand using the '-h' flag.

    Args:
        tool_name: The name of the CLI tool.
        subcommand: The subcommand (optional).
    """
    try:
        command = [tool_name]
        if subcommand:
            command.append(subcommand)
        command.append("-h")
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"

    except FileNotFoundError:
        return f"Error: Command '{tool_name}' not found."
```

**Task 3: Implement the `man` Page Tool**

*   **Files Involved:** `cli_explainer.py`
*   **Description:**
    *   Create a function `get_man_page(tool_name: str) -> str` that:
        *   Takes the `tool_name` (str) as input.
        *   Constructs the command to run (e.g., `man tool_name`).
        *   Uses `subprocess.run` to execute the command, capturing `stdout` and `stderr`. Use `check=False` and check the return code.
        *   Returns the captured output (stdout) as a string.  If there's an error, return an error message string.
        *   Handles potential `FileNotFoundError` gracefully.
        *   Include a clear docstring.
*   **Example Code Snippet:**

```python
def get_man_page(tool_name: str) -> str:
    """Gets the man page for a tool.

    Args:
      tool_name: the name of the tool
    """
    try:
        command = ["man", tool_name]
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error getting man page: {result.stderr}"

    except FileNotFoundError:
        return "Error: 'man' command not found.  Is it installed?"
```

**Task 4: Create the Pydantic-AI Agent**

*   **Files Involved:** `cli_explainer.py`
*   **Description:**
    *   Create a `pydantic_ai.Agent` instance.
    *   Set the `system_prompt` to instruct the agent on its role and *how to recursively explore subcommands*. This is the most critical part. The prompt should:
        *   Tell the agent to first get help for the main tool.
        *   Instruct it to *analyze the help text* to find potential subcommands.
        *   Tell it to *recursively* call `get_help_text` with any identified subcommands.
        *   Explain when to use `get_man_page` (if `get_help_text` fails or as a supplement).
        *   Instruct the agent to synthesize all gathered information to answer the user's query.
    *   Register the `get_help_text` and `get_man_page` functions as tools using `@agent.tool`.
    *   Set `deps_type` to `CLIQuery`.
    *   Choose an appropriate LLM model (e.g., "google-gla:gemini-1.5-flash").
*   **Example Code Snippet:**

```python
from pydantic_ai import Agent, RunContext

def create_agent():
    system_prompt = """
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
"""

    agent = Agent(
        system_prompt=system_prompt,
        tools=[get_help_text, get_man_page],
        deps_type=CLIQuery,
        model="google-gla:gemini-1.5-flash",  # Or an appropriate model
    )
    return agent
```

**Task 5: Build the Chat Interface with `rich`**

*   **Files Involved:** `cli_explainer.py`
*   **Description:**
    *   Import necessary components from `rich` (e.g., `Console`, `Panel`, `Markdown`).
    *   Create a `Console` instance.
    *   Implement a loop:
        *   Prompt the user for input (the CLI tool and their question).
        *   Create a `CLIQuery` object from the user's input.
        *   Call `agent.run_sync`, passing the `CLIQuery` as the `deps` argument.  The initial prompt can be an empty string, as all information is now in the deps.
        *   Use `rich` to format and display the agent's response (likely using `Markdown` for formatted output).
        *   Continue the loop until the user exits (e.g., types "quit").
        *   Handle `KeyboardInterrupt` and other potential exceptions gracefully.
*   **Example Code Snippet:**

```python
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

def run_chat_interface(agent: Agent):
    console = Console()
    console.print(Panel("[bold]CLI Tool Explainer[/bold]", border_style="green"))

    while True:
        try:
            user_input = console.input(
                "[bold]Enter the CLI tool and your question (or 'quit' to exit):[/bold] "
            )
            if user_input.lower() == "quit":
                break

            parts = user_input.split(" ", 1)
            if len(parts) < 2:
                console.print("[red]Please enter a tool name and a question.[/red]")
                continue
            tool_name, query = parts[0], parts[1]

            cli_query = CLIQuery(tool_name=tool_name, query=query)

            with console.status("Thinking..."):
                final_result = agent.run_sync("", deps=cli_query)

            console.print(
                Panel(Markdown(final_result.data), title="Explanation", border_style="blue")
            )

        except KeyboardInterrupt:
            console.print("\n[bold]Exiting...[/bold]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")
```

**Task 6: Main Function**

*   **Files Involved:** `cli_explainer.py`
*   **Description:**
    *   Create a `main` function to:
        *   Instantiate the `Agent`.
        *   Start the chat interface.
* **Example code Snippet:**

```python
def main():
    """Main function to run the application."""
    agent = create_agent()
    run_chat_interface(agent)

if __name__ == "__main__":
    main()
```

**Complete Code:**

```python
import asyncio
import subprocess
from typing import Optional

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


class CLIQuery(BaseModel):
    tool_name: str
    query: str


def get_help_text(tool_name: str, subcommand: Optional[str] = None) -> str:
    """Gets help text for a tool or subcommand using the '-h' flag.

    Args:
        tool_name: The name of the CLI tool.
        subcommand: The subcommand (optional).
    """
    try:
        command = [tool_name]
        if subcommand:
            command.append(subcommand)
        command.append("-h")
        result = subprocess.run(
            command, capture_output=True, text=True, check=False
        )  # check=False

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"  # store the error

    except FileNotFoundError:
        return f"Error: Command '{tool_name}' not found."


def get_man_page(tool_name: str) -> str:
    """Gets the man page for a tool.

    Args:
      tool_name: the name of the tool
    """
    try:
        command = ["man", tool_name]
        result = subprocess.run(
            command, capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error getting man page: {result.stderr}"

    except FileNotFoundError:
        return "Error: 'man' command not found.  Is it installed?"


def create_agent():
    system_prompt = """
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
"""

    agent = Agent(
        system_prompt=system_prompt,
        tools=[get_help_text, get_man_page],
        deps_type=CLIQuery,
        model="google-gla:gemini-1.5-flash",  # Or an appropriate model
    )
    return agent



def run_chat_interface(agent: Agent):
    console = Console()
    console.print(Panel("[bold]CLI Tool Explainer[/bold]", border_style="green"))

    while True:
        try:
            user_input = console.input(
                "[bold]Enter the CLI tool and your question (or 'quit' to exit):[/bold] "
            )
            if user_input.lower() == "quit":
                break

            parts = user_input.split(" ", 1)
            if len(parts) < 2:
                console.print("[red]Please enter a tool name and a question.[/red]")
                continue
            tool_name, query = parts[0], parts[1]

            cli_query = CLIQuery(tool_name=tool_name, query=query)

            with console.status("Thinking..."):
                final_result = agent.run_sync("", deps=cli_query)

            console.print(
                Panel(Markdown(final_result.data), title="Explanation", border_style="blue")
            )

        except KeyboardInterrupt:
            console.print("\n[bold]Exiting...[/bold]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")

def main():
    """Main function to run the application."""
    agent = create_agent()
    run_chat_interface(agent)

if __name__ == "__main__":
    main()
```

This plan and code fully embrace the LLM-driven approach, making the agent responsible for all tool calls and subcommand discovery.
