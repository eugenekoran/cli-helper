#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

import openai
import rich_click as click
from rich.console import Console
from rich.table import Table

from llm import CommandResult, OpenAIClient, LLMConfig, LLMClientError


def present_options(suggestions: list[dict[str, str]]) -> str | None:
    """Present command options to user and return selected command using interactive dropdown"""
    console = Console()
    
    # Create a table to display commands
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim")
    table.add_column("Command", style="green") 
    table.add_column("Description", style="blue")
    
    # Add commands to table
    for idx, cmd in enumerate(suggestions, 1):
        table.add_row(str(idx), cmd["command"], cmd["description"])
    
    # Display the table
    console.print("\n", table, "\n")
    # Add cancel option
    total_options = len(suggestions)
    console.print(f"{total_options + 1}: Cancel - don't execute any command\n")
    
    while True:
        choice = click.prompt("Select a command", type=str, default="1")
        
        try:
            choice_idx = int(choice)
            if 1 <= choice_idx <= total_options:
                return suggestions[choice_idx - 1]["command"]
            elif choice_idx == total_options + 1:
                return
            else:
                console.print("[red]Invalid choice. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")


def execute_command(command: str) -> CommandResult:
    """Execute the suggested command and return the result"""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    except Exception as e:
        return {
            "command": command,
            "stdout": None,
            "stderr": str(e),
            "success": False
        }

def detect_shell() -> str:
    """Detect current shell from SHELL environment variable"""
    return os.path.basename(os.environ.get("SHELL", "unknown"))


def main():
    parser = argparse.ArgumentParser(description="LLM-powered CLI helper")
    parser.add_argument("--model", type=str, default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--max-tokens", type=int, default=1_000, help="Maximum tokens for response")
    parser.add_argument("-q", "--question", type=str, help="Initial question to start with")
    args = parser.parse_args()

    # Add shell detection
    current_shell = detect_shell()
    if current_shell not in ["bash", "zsh", "fish"]:
        print(f"Warning: Unsupported shell detected: {current_shell}")
        if not click.confirm("Continue anyway?", default=True):
            sys.exit(1)

    # Check for OpenAI API key
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set your OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    openai.api_key = os.environ["OPENAI_API_KEY"]

    console = Console()
    config = LLMConfig(
        model=args.model,
        max_tokens=args.max_tokens
    )
    llm_client = OpenAIClient(config, current_shell)

    # Initialize conversation history
    initial_query = args.question
    skip_input = False
    
    print("Welcome to LLM CLI Helper! (Type 'exit' to quit)")
    print("Type 'clear' to start a new conversation")
    
    while True:
        try:
            if not skip_input:
                if initial_query:
                    user_input = initial_query
                    initial_query = None
                else:
                    user_input = input("\nWhat would you like to do? > ")

                if user_input.lower() in ["exit", "quit"]:
                    break

                if user_input.lower() == "clear":
                    llm_client.clear_history()
                    console.print("Conversation history cleared!")
                    continue

                if not user_input.strip():
                    continue

                # Add user input to conversation history
                llm_client.get_user_input(user_input)
                console_args = dict(status="[bold green]Thinking...[/bold green]", spinner_style="green", spinner="dots")
            else:
                # When handling error, just continue with the existing context
                console_args = dict(status="[bold red]Handling error...[/bold red]", spinner_style="red", spinner="dots")
                skip_input = False

            with console.status(**console_args):
                response = llm_client.respond()

            # Handle different types of responses
            if isinstance(response, str):
                console.print(response)
            elif isinstance(response, dict):
                if response.get("needs_more_info"):
                    question = response.get("follow_up_question", "Could you provide more details?")
                    console.print(question)
                    llm_client.handle_follow_up_question(question)
                else:
                    selected_command = present_options(response["commands"])
                    if selected_command:
                        console.print(">>", selected_command, style="green")
                        result = execute_command(selected_command)
                        llm_client.handle_command_execution(result)

                        # Display command output
                        if result["success"]:
                            print(result["stdout"])
                        else:
                            print("Error:", result["stderr"])
                            skip_input = True
                    else:
                        # User cancelled the command execution
                        llm_client.handle_command_abort("User cancelled command execution")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except LLMClientError as e:
            console.print(f"[red]LLM Error: {e}[/red]")
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")


if __name__ == "__main__":
    main()
