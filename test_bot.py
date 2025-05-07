"""
Test script to run the Meeting Rescheduler chatbot locally.
"""

import os
from dotenv import load_dotenv
from src.chatbot import create_chatbot

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please create a .env file with your OPENAI_API_KEY"
        )
    
    # Create and launch the chatbot interface
    interface = create_chatbot(openai_api_key=api_key)
    
    # Launch with queue for async operations
    interface.queue().launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,  # Default Gradio port
        share=True  # Create a public link
    )

if __name__ == "__main__":
    main() 