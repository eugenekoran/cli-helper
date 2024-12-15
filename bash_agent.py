import json
import os
import subprocess
from typing import Any, Dict, List

import openai

class BashAgent:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        
        # Define the bash command tool
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_bash",
                    "description": "Execute a bash command and return its output",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The bash command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ]

    def execute_bash(self, command: str, timeout: int = 10) -> Dict[str, Any]:
        """Execute a bash command and return the output and error if any."""
        try:
            # Using subprocess.run with capture_output to get both stdout and stderr
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "output": result.stdout,
                "error": result.stderr,
                "status": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "output": "",
                "error": "Command execution timed out",
                "status": -1
            }
        except Exception as e:
            return {
                "output": "",
                "error": str(e),
                "status": -1
            }

    def process_tool_calls(self, tool_calls: list) -> List[Dict[str, Any]]:
        """Process tool calls and return their results."""
        results = []
        
        for tool_call in tool_calls:
            if tool_call.function.name == "execute_bash":
                # Parse the arguments
                args = json.loads(tool_call.function.arguments)
                # Execute the command
                result = self.execute_bash(args["command"])
                results.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result)
                })
                
        return results

    def run(self, prompt: str) -> str:
        """Run the agent with a given prompt."""
        # Initial message to the model
        messages = [{"role": "user", "content": prompt}]
        
        while True:
            # Get response from the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # If no tool calls, return the message content
            if not message.tool_calls:
                return message.content
            
            # Process tool calls and add results to messages
            results = self.process_tool_calls(message.tool_calls)
            messages.append(message)
            
            # Add tool results to messages
            for result in results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result["tool_call_id"],
                    "content": result["output"]
                })

# Example usage
def main():
    # Replace with your OpenAI API key
    api_key = os.environ["OPENAI_API_KEY"]
    agent = BashAgent(api_key)
    
    # Example prompts
    prompts = [
        "List all files in the current directory",
        "Show me system information using neofetch if installed, otherwise show uname -a",
        "Create a new directory called 'test' and list its contents"
    ]
    
    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        print("Response:")
        response = agent.run(prompt)
        print(response)

if __name__ == "__main__":
    main()