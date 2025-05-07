"""
Conversation management for the Meeting Rescheduler Agent.
Handles all LLM interactions and maintains conversation state.
"""

import os
from typing import List, Dict, Optional, Tuple, Any
import openai
from openai import AsyncOpenAI
from .state import StateManager
from .templates import PromptTemplates

class Message:
    """Simple message class to replace LangChain's message types."""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

class ConversationManager:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the conversation manager.
        
        Args:
            api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please provide it or set OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.state_manager = StateManager()
        self.templates = PromptTemplates()
        
        # Initialize conversation with system message
        self.messages: List[Message] = [
            Message("system", self.templates.get_system_prompt())
        ]
        
        # Initialize chat history
        self.history: List[List[str]] = []
    
    def add_message(self, message: str, is_human: bool = True) -> None:
        """Add a message to the conversation history.
        
        Args:
            message: The message content
            is_human: Whether the message is from the human (True) or AI (False)
        """
        role = "user" if is_human else "assistant"
        self.messages.append(Message(role, message))
        
        # Update chat history for Gradio display
        if is_human:
            self.history.append([message, None])
        else:
            if self.history:
                self.history[-1][1] = message
    
    async def get_response(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """Get a response from the LLM for the given message.
        
        Args:
            message: The user's message
            
        Returns:
            Tuple of (response text, updated state)
        """
        # Add user message to history
        self.add_message(message, is_human=True)
        
        # Get current state and add to context
        current_state = self.state_manager.get_state()
        context_message = self.templates.get_state_prompt(current_state)
        
        # Add state context as a system message
        messages_for_api = [msg.to_dict() for msg in self.messages]
        messages_for_api.append({"role": "system", "content": context_message})
        
        try:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages_for_api,
                temperature=0.7,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content
            
            # Add AI response to history
            self.add_message(response_text, is_human=False)
            
            # Update state based on response
            updated_state = self.state_manager.update_from_response(response_text)
            
            return response_text, updated_state
            
        except Exception as error:
            error_message = f"Error getting LLM response: {str(error)}"
            self.state_manager.set_error(error_message)
            raise
    
    def clear_history(self) -> None:
        """Clear the conversation history but keep the system message."""
        self.messages = [self.messages[0]]  # Keep system message
        self.history = []
        self.state_manager.reset()
    
    def get_history(self) -> List[List[str]]:
        """Get the conversation history in a format suitable for Gradio chatbot.
        
        Returns:
            List of message pairs [user_message, bot_message]
        """
        return self.history 