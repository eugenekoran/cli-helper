COMMAND_TOOLS = [
    {
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
                                "command": {
                                    "type": "string",
                                    "description": "The bash command to execute"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Brief description of what the command does"
                                },
                                "safety_level": {
                                    "type": "string",
                                    "enum": ["safe", "caution", "dangerous"],
                                    "description": "Indicates the safety level of the command"
                                }
                            },
                            "required": ["command", "description", "safety_level"]
                        }
                    },
                    "needs_more_info": {"type": "boolean"},
                    "follow_up_question": {"type": "string"}
                },
                "required": ["commands", "needs_more_info"]
            }
        }
    }
] 