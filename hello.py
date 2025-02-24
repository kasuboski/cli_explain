import subprocess
from pydantic_ai import Agent, RunContext

# Create a new agent with an OpenAI compatible model
agent = Agent('openai:text-davinci-003', deps_type=str)

# Tool to check if a CLI is installed
@agent.tool_plain
def is_installed(tool_name: str) -> bool:
    """Check if a CLI tool is installed."""
    try:
        subprocess.run([tool_name, '--version'], check=True, stdout=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

# Tool to call a CLI with a configurable command and -h or --help
@agent.tool_plain
def get_cli_help(tool_name: str, command: str = '') -> str:
    """Get the help text for a CLI tool."""
    try:
        output = subprocess.check_output([tool_name] + command.split() + ['-h'], text=True)
        return output
    except FileNotFoundError:
        return f"{tool_name} is not installed."
    except subprocess.CalledProcessError as e:
        return f"Failed to get help text for {tool_name}: {e}"

# Tool to search manpages for a tool
@agent.tool_plain
def get_manpage(tool_name: str) -> str:
    """Get the manpage for a CLI tool."""
    try:
        output = subprocess.check_output(['man', tool_name], text=True)
        return output
    except FileNotFoundError:
        return f"Manpage for {tool_name} not found."
    except subprocess.CalledProcessError as e:
        return f"Failed to get manpage for {tool_name}: {e}"

# Run the agent
def main():
    result = agent.run_sync('Explain the cli tool git')
    print(result.data)

if __name__ == "__main__":
    main()
