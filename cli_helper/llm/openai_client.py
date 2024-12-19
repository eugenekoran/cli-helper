import json
from typing import Any, Dict, List, Optional, Union

import openai

from .base import BaseLLMClient, LLMConfig, LLMClientError, CommandResult
from .tools import COMMAND_TOOLS

class OpenAIClient(BaseLLMClient):
    def __init__(self, config: LLMConfig, shell: str):
        super().__init__(config, shell)
        self._last_tool_call: Optional[Dict[str, Any]] = None

    def _get_tools(self) -> List[Dict[str, Any]]:
        return COMMAND_TOOLS

    def respond(self) -> Union[Dict[str, Any], str]:
        return self._get_llm_response()
    
    def get_user_input(self, user_input: str) -> None:
        self.conversation_history.append({"role": "user", "content": user_input})

    def handle_follow_up_question(self, question: str) -> None:
        if not self._last_tool_call:
            raise LLMClientError("No previous tool call found")
            
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": self._last_tool_call["id"],
            "content": json.dumps({
                "needs_more_info": True,
                "follow_up_question": question,
                "user_response": "pending"
            })
        })

    def handle_command_execution(self, command_result: CommandResult) -> None:
        if not self._last_tool_call:
            raise LLMClientError("No previous tool call found")
            
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": self._last_tool_call["id"],
            "content": json.dumps(command_result)
        })

    def handle_command_abort(self, reason: str) -> None:
        if not self._last_tool_call:
            raise LLMClientError("No previous tool call found")
            
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": self._last_tool_call["id"],
            "content": json.dumps({
                "command": None,
                "cancelled": True,
                "reason": reason
            })
        })

    def _get_llm_response(self) -> Union[Dict[str, Any], str]:
        """Fetches and processes a response from the OpenAI API.

        Constructs messages from the system prompt and conversation history,
        sends them to the OpenAI API, and returns the processed response.

        Returns:
            Union[Dict[str, Any], str]: The LLM's response, either as a tool call
            dictionary or a simple string message.

        Raises:
            LLMClientError: For API errors, rate limits, connection issues, or unexpected errors.
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.conversation_history
            ]
            
            response = openai.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            return self._process_response(response)
            
        except openai.APIError as e:
            raise LLMClientError(f"OpenAI API error: {e}")
        except openai.RateLimitError as e:
            raise LLMClientError(f"Rate limit exceeded: {e}")
        except openai.APIConnectionError as e:
            raise LLMClientError(f"Connection error: {e}")
        except Exception as e:
            raise LLMClientError(f"Unexpected error: {e}")

    def _process_response(self, response: Any) -> Union[Dict[str, Any], str]:
        """Process OpenAI API response and update conversation history"""
        assistant_message = response.choices[0].message
        
        message_entry = {
            "role": "assistant",
            "content": assistant_message.content,
        }

        if assistant_message.tool_calls:
            message_entry["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                for tool_call in assistant_message.tool_calls
            ]
            # Store the last tool call for future reference
            self._last_tool_call = message_entry["tool_calls"][0]

        self.conversation_history.append(message_entry)

        if assistant_message.tool_calls:
            tool_call = assistant_message.tool_calls[0]
            return json.loads(tool_call.function.arguments)
        
        return assistant_message.content