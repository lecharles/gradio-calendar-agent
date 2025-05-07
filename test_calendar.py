import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import Dict, List, Any

class SimpleCalendarTool:
    """A simplified version of the calendar tool for testing."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.creds = None
        self.calendar_service = None
        
    def authenticate(self) -> bool:
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
            return True
        except Exception as e:
            print(f"Error building services: {e}")
            return False
    
    def get_events(self, start_date: datetime, end_date: datetime) -> Dict[str, List[Dict[str, Any]]]:
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

def test_calendar_reading():
    # Initialize the calendar tool
    calendar = SimpleCalendarTool()
    
    # Authenticate
    print("Authenticating with Google Calendar...")
    if not calendar.authenticate():
        print("Failed to authenticate!")
        return
    
    # Get events for the next week
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    
    print(f"\nFetching events from {start_date.date()} to {end_date.date()}...")
    try:
        events = calendar.get_events(start_date, end_date)
        
        print("\nRecurring Meetings:")
        for event in events['recurring']:
            print(f"- {event.get('summary', 'Untitled')} (ID: {event['id']})")
        
        print("\nOne-off Meetings:")
        for event in events['one_off']:
            start_time = event.get('start', {}).get('dateTime', 'unknown date')
            print(f"- {event.get('summary', 'Untitled')} on {start_time} (ID: {event['id']})")
            
    except Exception as e:
        print(f"Error fetching events: {e}")

if __name__ == "__main__":
    test_calendar_reading() 