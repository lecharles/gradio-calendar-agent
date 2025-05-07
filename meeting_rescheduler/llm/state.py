"""
State management for the Meeting Rescheduler Agent.
Handles tracking and updating the conversation state.
"""

from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class CalendarEvent(BaseModel):
    """Model for calendar events."""
    event_id: str
    summary: str
    start_time: datetime
    end_time: datetime
    is_recurring: bool
    attendees: List[str]
    organizer: str
    status: str = "pending"  # pending, cancelled, notified

class ConversationState(BaseModel):
    """Model for conversation state."""
    authenticated: bool = False
    time_off_start: Optional[datetime] = None
    time_off_end: Optional[datetime] = None
    recurring_meetings: List[CalendarEvent] = Field(default_factory=list)
    one_off_meetings: List[CalendarEvent] = Field(default_factory=list)
    current_meeting_index: int = 0
    email_templates: Dict[str, str] = Field(default_factory=dict)
    current_action: Optional[str] = None  # authenticate, set_dates, review_meetings, etc.
    last_error: Optional[str] = None

class StateManager:
    def __init__(self):
        """Initialize the state manager."""
        self.state = ConversationState()
    
    def get_state(self) -> Dict:
        """Get the current state as a dictionary."""
        return self.state.model_dump()
    
    def update_state(self, **kwargs) -> None:
        """Update specific state fields."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
    
    def update_from_response(self, response: str) -> Dict:
        """Update state based on LLM response.
        
        This method analyzes the LLM response and updates the state accordingly.
        It looks for specific patterns that indicate state changes.
        
        Args:
            response: The LLM's response text
            
        Returns:
            Updated state as dictionary
        """
        # TODO: Implement response parsing logic
        # This will involve looking for specific patterns in the response
        # that indicate state changes, such as:
        # - Authentication status changes
        # - Time off date settings
        # - Meeting status updates
        # - Email template changes
        
        return self.get_state()
    
    def add_calendar_event(self, event_data: Dict, is_recurring: bool) -> None:
        """Add a calendar event to the state.
        
        Args:
            event_data: Dictionary containing event information
            is_recurring: Whether this is a recurring meeting
        """
        event = CalendarEvent(
            event_id=event_data['id'],
            summary=event_data['summary'],
            start_time=event_data['start_time'],
            end_time=event_data['end_time'],
            is_recurring=is_recurring,
            attendees=event_data['attendees'],
            organizer=event_data['organizer']
        )
        
        if is_recurring:
            self.state.recurring_meetings.append(event)
        else:
            self.state.one_off_meetings.append(event)
    
    def update_meeting_status(self, event_id: str, status: str) -> None:
        """Update the status of a meeting.
        
        Args:
            event_id: The ID of the event to update
            status: New status (pending, cancelled, notified)
        """
        for meetings in [self.state.recurring_meetings, self.state.one_off_meetings]:
            for meeting in meetings:
                if meeting.event_id == event_id:
                    meeting.status = status
                    break
    
    def set_current_action(self, action: str) -> None:
        """Set the current action being performed.
        
        Args:
            action: The current action (authenticate, set_dates, review_meetings, etc.)
        """
        self.state.current_action = action
    
    def set_error(self, error: str) -> None:
        """Set the last error message.
        
        Args:
            error: Error message
        """
        self.state.last_error = error
    
    def clear_error(self) -> None:
        """Clear the last error message."""
        self.state.last_error = None
    
    def reset(self) -> None:
        """Reset the state to initial values."""
        self.state = ConversationState() 