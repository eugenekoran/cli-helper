#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

import openai
import rich_click as click
from rich.console import Console
from rich.table import Table


def get_llm_response(prompt: str, current_shell: str, conversation_history: list, model: str, max_tokens: int) -> dict | str | None:
    """Get response from OpenAI API with conversation context"""
    try:
        tools = [{
            "type": "function",
            "function": {
                "name": "suggest_commands",
                "description": "Suggest multiple bash commands to accomplish the task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "commands": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string", "description": "The bash command to execute"},
                                    "description": {"type": "string", "description": "Brief description of what the command does"}
                                },
                                "required": ["command", "description"]
                            }
                        },
                        "needs_more_info": {
                            "type": "boolean",
                            "description": "Set to true if more information is needed from the user"
                        },
                        "follow_up_question": {
                            "type": "string",
                            "description": "Question to ask the user for additional information"
                        }
                    },
                    "required": ["commands", "needs_more_info"]
                }
            }
        }]

        # Build messages with conversation history
        messages = [
            {
                "role": "system", 
                "content": f"""You are a helpful CLI assistant running in {current_shell} shell. Your sole purpose is to help users with command-line tasks.

                Response Guidelines:
                1. For command-line tasks:
                   - ALWAYS use the suggest_commands tool to provide command suggestions
                   - If details are insufficient, use suggest_commands with needs_more_info=True
                   - Include a relevant follow_up_question to gather missing information

                2. For general shell-related questions:
                   - Explain the concepts or options clearly
                   - Guide the user towards formulating a specific command request
                   - Ask for necessary details to construct an executable command

                3. For non-CLI related questions:
                   - If it's a greeting or question about your CLI capabilities, respond directly
                   - For all other non-CLI topics, politely remind the user that you're a CLI assistant
                   - Suggest they ask about command-line tasks instead
                   Example: "I'm a CLI assistant focused on helping with command-line tasks. If you have any questions about using the terminal, running commands, or managing files and processes, I'd be happy to help!"

                IMPORTANT:
                - NEVER provide shell commands directly in messages
                - ALWAYS use the suggest_commands tool for any command suggestions

                When using suggest_commands:
                - Provide multiple command options when possible
                - Commands must be fully executable (no placeholder paths)
                - Use relative paths unless absolute paths are specifically requested
                - Each command should have a clear, concise description
                """
            }
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })

        response = openai.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=max_tokens
        )

        # Store the assistant's response in conversation history
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            result = json.loads(tool_call.function.arguments)
            conversation_history.append({"role": "assistant", "content": json.dumps(result)})
            return result
        else:
            content = response.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": content})
            return content

    except Exception as e:
        print(f"Error getting LLM response: {e}")
        sys.exit(1)


def present_options(suggestions: list[dict]) -> str | None:
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
                return None
            else:
                console.print("[red]Invalid choice. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")


def execute_command(command: str) -> None:
    """Execute the suggested command"""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print("Error:", result.stderr)
    except Exception as e:
        print(f"Error executing command: {e}")


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

    # Initialize conversation history
    conversation_history = []
    initial_query = args.question
    
    print("Welcome to LLM CLI Helper! (Type 'exit' to quit)")
    print("Type 'clear' to start a new conversation")
    
    while True:
        try:
            if initial_query:
                user_input = initial_query
                initial_query= None
            else:
                user_input = input("\nWhat would you like to do? > ")
            
            if user_input.lower() in ["exit", "quit"]:
                break

            if user_input.lower() == "clear":
                conversation_history = []
                print("Conversation history cleared!")
                continue

            if not user_input.strip():
                continue

            # Add user input to conversation history
            conversation_history.append({"role": "user", "content": user_input})

            with console.status("[bold green]Thinking...", spinner="dots"):
                response = get_llm_response(user_input, current_shell, conversation_history, args.model, args.max_tokens)
            
            # Handle different types of responses
            if isinstance(response, str):
                console.print(response)
            elif isinstance(response, dict):
                if response.get("needs_more_info"):
                    console.print(response.get("follow_up_question", "Could you provide more details?"))
                else:
                    selected_command = present_options(response["commands"])
                    if selected_command:
                        console.print(">>", selected_command, style="green")
                        execute_command(selected_command)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
