from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import json
import pickle

class CalendarTool:
    """A tool for managing Google Calendar events and sending emails."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/gmail.send'
    ]
    
    def __init__(self):
        """Initialize the calendar tool with Google API credentials."""
        self.creds = None
        self.calendar_service = None
        self.gmail_service = None
        
    def authenticate(self) -> bool:
        """Authenticate with Google Calendar and Gmail APIs."""
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
                
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
        
        try:
            self.calendar_service = build('calendar', 'v3', credentials=self.creds)
            self.gmail_service = build('gmail', 'v1', credentials=self.creds)
            return True
        except Exception as e:
            print(f"Error building services: {e}")
            return False
    
    def get_events(self, start_date: datetime, end_date: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """Get all events between start_date and end_date, classified as recurring or one-off."""
        if not self.calendar_service:
            raise ValueError("Calendar service not initialized. Call authenticate() first.")
            
        events_result = self.calendar_service.events().list(
            calendarId='primary',
            timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Classify events
        recurring_events = []
        one_off_events = []
        
        for event in events:
            if 'recurrence' in event:
                recurring_events.append(event)
            else:
                one_off_events.append(event)
                
        return {
            'recurring': recurring_events,
            'one_off': one_off_events
        }
    
    def cancel_event(self, event_id: str, send_notification: bool = True) -> bool:
        """Cancel a specific event."""
        if not self.calendar_service:
            raise ValueError("Calendar service not initialized. Call authenticate() first.")
            
        try:
            self.calendar_service.events().delete(
                calendarId='primary',
                eventId=event_id,
                sendNotifications=send_notification
            ).execute()
            return True
        except Exception as e:
            print(f"Error canceling event: {e}")
            return False
    
    def send_rescheduling_email(self, event: Dict[str, Any], message: str) -> bool:
        """Send an email to event attendees about rescheduling."""
        if not self.gmail_service:
            raise ValueError("Gmail service not initialized. Call authenticate() first.")
            
        attendees = event.get('attendees', [])
        if not attendees:
            return False
            
        email_addresses = [attendee['email'] for attendee in attendees if 'email' in attendee]
        
        try:
            # Create email message
            email_content = {
                'to': ', '.join(email_addresses),
                'subject': f"Rescheduling: {event.get('summary', 'Meeting')}",
                'message': message
            }
            
            # TODO: Implement actual email sending using Gmail API
            # For now, just print the email content
            print(f"Would send email:\n{json.dumps(email_content, indent=2)}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific event."""
        if not self.calendar_service:
            raise ValueError("Calendar service not initialized. Call authenticate() first.")
            
        try:
            event = self.calendar_service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            return event
        except Exception as e:
            print(f"Error getting event details: {e}")
            return None

    def create_event(self, summary: str, start_time: datetime, end_time: datetime, 
                    description: str = "", location: str = "", attendees: List[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new calendar event."""
        if not self.calendar_service:
            raise ValueError("Calendar service not initialized. Call authenticate() first.")
            
        try:
            event_body = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]
            
            event = self.calendar_service.events().insert(
                calendarId='primary',
                body=event_body,
                sendUpdates='all'
            ).execute()
            
            return event
        except Exception as e:
            print(f"Error creating event: {e}")
            return None

    def get_upcoming_events_count(self, days: int = 7) -> Tuple[int, Dict[str, List[Dict[str, Any]]]]:
        """Get the count and details of upcoming events for the next N days."""
        if not self.calendar_service:
            raise ValueError("Calendar service not initialized. Call authenticate() first.")
            
        start = datetime.utcnow()
        end = start + timedelta(days=days)
        
        events = self.get_events(start, end)
        total_count = len(events['recurring']) + len(events['one_off'])
        
        return total_count, events 