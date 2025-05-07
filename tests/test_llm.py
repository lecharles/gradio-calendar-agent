"""
Tests for the LLM integration package.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.llm.conversation import ConversationManager, Message
from src.llm.state import StateManager, CalendarEvent
from src.llm.templates import PromptTemplates

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    class MockChoice:
        def __init__(self, text):
            self.message = MagicMock()
            self.message.content = text
    
    class MockResponse:
        def __init__(self, text):
            self.choices = [MockChoice(text)]
    
    return MockResponse("I'll help you manage your calendar.")

@pytest.fixture
def conversation_manager():
    """Create a ConversationManager with a mock API key."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        return ConversationManager()

@pytest.mark.asyncio
async def test_conversation_flow(conversation_manager, mock_openai_response):
    """Test the basic conversation flow."""
    # Mock the OpenAI client
    conversation_manager.client = AsyncMock()
    conversation_manager.client.chat.completions.create.return_value = mock_openai_response
    
    # Test sending a message
    response, state = await conversation_manager.get_response("Hi, I need to manage my calendar.")
    
    # Verify the response
    assert response == "I'll help you manage your calendar."
    assert len(conversation_manager.messages) == 3  # System + User + Assistant
    assert conversation_manager.messages[1].role == "user"
    assert conversation_manager.messages[2].role == "assistant"

def test_state_management():
    """Test the state management functionality."""
    state_manager = StateManager()
    
    # Test initial state
    assert state_manager.get_state()['authenticated'] == False
    assert state_manager.get_state()['recurring_meetings'] == []
    
    # Test updating state
    state_manager.update_state(authenticated=True)
    assert state_manager.get_state()['authenticated'] == True
    
    # Test adding a calendar event
    event_data = {
        'id': 'test123',
        'summary': 'Test Meeting',
        'start_time': datetime.now(),
        'end_time': datetime.now(),
        'attendees': ['test@example.com'],
        'organizer': 'organizer@example.com'
    }
    
    state_manager.add_calendar_event(event_data, is_recurring=True)
    assert len(state_manager.get_state()['recurring_meetings']) == 1
    
    # Test updating meeting status
    state_manager.update_meeting_status('test123', 'cancelled')
    assert state_manager.get_state()['recurring_meetings'][0].status == 'cancelled'

def test_prompt_templates():
    """Test the prompt templates functionality."""
    templates = PromptTemplates()
    
    # Test system prompt
    system_prompt = templates.get_system_prompt()
    assert "You are a helpful meeting rescheduler assistant" in system_prompt
    
    # Test state prompt
    state = {
        'authenticated': True,
        'time_off_start': '2024-03-20',
        'time_off_end': '2024-03-25',
        'recurring_meetings': [1, 2],  # Just testing length
        'one_off_meetings': [1]  # Just testing length
    }
    
    state_prompt = templates.get_state_prompt(state)
    assert "✓ User is authenticated" in state_prompt
    assert "Found 2 recurring meetings" in state_prompt
    assert "Found 1 one-off meetings" in state_prompt
    
    # Test email templates
    recurring_template = templates.get_email_template('recurring')
    assert "Cancellation Notice" in recurring_template
    assert "{meeting_name}" in recurring_template
    
    one_off_template = templates.get_email_template('one_off')
    assert "Unable to Attend" in one_off_template
    assert "Would it be possible to reschedule" in one_off_template

def test_message_class():
    """Test the Message class functionality."""
    # Test user message
    user_msg = Message("user", "Hello")
    assert user_msg.role == "user"
    assert user_msg.content == "Hello"
    assert user_msg.to_dict() == {"role": "user", "content": "Hello"}
    
    # Test system message
    system_msg = Message("system", "You are a helpful assistant")
    assert system_msg.role == "system"
    assert system_msg.to_dict() == {"role": "system", "content": "You are a helpful assistant"}

def test_conversation_history(conversation_manager):
    """Test the conversation history management."""
    # Add some messages
    conversation_manager.add_message("Hello", is_human=True)
    conversation_manager.add_message("Hi there!", is_human=False)
    
    # Check history format
    history = conversation_manager.get_history()
    assert len(history) == 1
    assert history[0] == ["Hello", "Hi there!"]
    
    # Test clearing history
    conversation_manager.clear_history()
    assert len(conversation_manager.get_history()) == 0
    assert len(conversation_manager.messages) == 1  # Only system message remains 