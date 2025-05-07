import os
import pytest
from datetime import datetime, timedelta
from meeting_rescheduler.calendar_tool import CalendarTool
from meeting_rescheduler.app import parse_date_range, format_events_message
from dotenv import load_dotenv

print("Starting test file execution...")

# Load environment variables
load_dotenv()
print("Environment variables loaded")

@pytest.fixture
def calendar_tool():
    print("Creating calendar tool...")
    tool = CalendarTool()
    print("Calendar tool created")
    return tool

def test_calendar_authentication(calendar_tool):
    """Test Google Calendar authentication."""
    print("Testing calendar authentication...")
    print(f"Current directory: {os.getcwd()}")
    print(f"credentials.json exists: {os.path.exists('credentials.json')}")
    assert os.path.exists('credentials.json'), "credentials.json not found. Please set up Google Calendar credentials first."
    success = calendar_tool.authenticate()
    print(f"Authentication result: {success}")
    assert success, "Calendar authentication failed"
    assert calendar_tool.calendar_service is not None
    assert calendar_tool.gmail_service is not None
    print("Calendar authentication test completed")

def test_date_parsing():
    """Test date parsing functionality."""
    test_cases = [
        ("I'll be away next week", None),  # Should return next week's dates
        ("I'm taking vacation from July 1st to July 15th", 
         ((7, 1), (7, 15))),  # Only check month and day
        ("Out of office December 24-26", 
         ((12, 24), (12, 26)))  # Only check month and day
    ]
    
    for input_text, expected in test_cases:
        start_date, end_date = parse_date_range(input_text)
        if expected:
            # Check only month and day, ignore year
            assert (start_date.month, start_date.day) == expected[0]
            assert (end_date.month, end_date.day) == expected[1]
        else:
            # For relative dates, just check if the range makes sense
            assert start_date < end_date
            assert (end_date - start_date).days >= 0

def test_event_retrieval(calendar_tool):
    """Test retrieving calendar events."""
    calendar_tool.authenticate()
    
    # Test next week's events
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    
    events = calendar_tool.get_events(start_date, end_date)
    assert isinstance(events, dict)
    assert 'recurring' in events
    assert 'one_off' in events
    assert isinstance(events['recurring'], list)
    assert isinstance(events['one_off'], list)

def test_event_formatting():
    """Test event formatting functionality."""
    sample_events = {
        'recurring': [{
            'id': 'rec1',
            'summary': 'Weekly Team Meeting',
            'start': {'dateTime': '2024-03-20T10:00:00Z'}
        }],
        'one_off': [{
            'id': 'single1',
            'summary': 'Client Presentation',
            'start': {'dateTime': '2024-03-21T14:00:00Z'}
        }]
    }
    
    formatted = format_events_message(sample_events)
    assert 'Weekly Team Meeting' in formatted
    assert 'Client Presentation' in formatted
    assert 'rec1' in formatted
    assert 'single1' in formatted

def test_event_cancellation(calendar_tool):
    """Test event cancellation functionality."""
    calendar_tool.authenticate()
    
    # First get an event to cancel
    start_date = datetime.now()
    end_date = start_date + timedelta(days=1)
    events = calendar_tool.get_events(start_date, end_date)
    
    if events['one_off']:
        test_event = events['one_off'][0]
        event_id = test_event['id']
        
        # Get event details before cancellation
        event_details = calendar_tool.get_event_details(event_id)
        assert event_details is not None
        
        # Try to cancel the event
        success = calendar_tool.cancel_event(event_id, send_notification=False)
        assert success, f"Failed to cancel event {event_id}"
        
        # Verify event is cancelled
        cancelled_details = calendar_tool.get_event_details(event_id)
        assert cancelled_details is None or cancelled_details.get('status') == 'cancelled'

def test_email_notification(calendar_tool):
    """Test email notification functionality."""
    calendar_tool.authenticate()
    
    # Create a test event structure
    test_event = {
        'id': 'test123',
        'summary': 'Test Meeting',
        'attendees': [
            {'email': 'test@example.com'},
            {'email': 'another@example.com'}
        ]
    }
    
    # Test sending rescheduling email
    message = "I'll be out next week. Let's reschedule this meeting when I return."
    success = calendar_tool.send_rescheduling_email(test_event, message)
    assert success, "Failed to send rescheduling email"

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 