from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict, Union

from .prompts import CLI_SYSTEM_PROMPT

@dataclass
class LLMConfig:
    model: str
    max_tokens: int
    temperature: float = 1.0


class CommandResult(TypedDict):
    command: str
    stdout: Optional[str]
    stderr: Optional[str]
    success: bool


class LLMClientError(Exception):
    """Base exception for LLM client errors"""
    pass


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    def __init__(self, config: LLMConfig, shell: str):
        self.config = config
        self.shell = shell
        self.tools = self._get_tools()
        self.system_prompt = self._get_system_prompt()
        self.conversation_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    def respond(self) -> Union[Dict[str, Any], str]:
        """Get response from LLM based on current conversation history"""
        pass

    @abstractmethod
    def get_user_input(self, user_input: str) -> None:
        """Add user input to conversation history"""
        pass

    @abstractmethod
    def handle_follow_up_question(self, question: str) -> None:
        """Add user's follow-up answer to conversation history"""
        pass

    @abstractmethod
    def handle_command_execution(self, command_result: CommandResult) -> None:
        """Add command execution results to conversation history"""
        pass

    @abstractmethod
    def handle_command_abort(self, reason: str) -> None:
        """Add command abort information to conversation history"""
        pass

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history = []

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return CLI_SYSTEM_PROMPT.format(shell=self.shell)

    @abstractmethod
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the LLM"""
        pass
