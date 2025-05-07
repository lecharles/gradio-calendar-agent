from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64
from .auth import authenticate

class CalendarService:
    def __init__(self):
        self.credentials = authenticate()
        self.service = build('calendar', 'v3', credentials=self.credentials)
        self.gmail_service = build('gmail', 'v1', credentials=self.credentials)

    def get_events(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Retrieve all events between start_date and end_date.
        Returns a list of event dictionaries.
        """
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])

    def classify_events(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Classify events as recurring or one-off.
        Returns a dictionary with two lists: 'recurring' and 'one_off'.
        """
        classified_events = {
            'recurring': [],
            'one_off': []
        }
        
        for event in events:
            # If the event has a recurrence rule, it's recurring
            if 'recurrence' in event:
                classified_events['recurring'].append(event)
            else:
                classified_events['one_off'].append(event)
        
        return classified_events

    def format_event_info(self, event: Dict) -> str:
        """
        Format event information for display.
        Returns a formatted string with event details.
        """
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        # Convert to datetime objects for better formatting
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        attendees = event.get('attendees', [])
        attendee_emails = [a['email'] for a in attendees if 'email' in a]
        
        return (
            f"Title: {event['summary']}\n"
            f"When: {start_dt.strftime('%Y-%m-%d %H:%M')} to "
            f"{end_dt.strftime('%Y-%m-%d %H:%M')}\n"
            f"Recurring: {'Yes' if 'recurrence' in event else 'No'}\n"
            f"Attendees: {', '.join(attendee_emails) if attendee_emails else 'No attendees'}\n"
        )

    def cancel_recurring_meetings(self, event_id: str, start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
        """
        Cancel instances of a recurring meeting within the specified date range.
        Returns a tuple of (success, message).
        """
        try:
            # Get the recurring event series
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            if 'recurrence' not in event:
                return False, "This is not a recurring event."

            # Create an exception for each instance in the date range
            instances = self.service.events().instances(
                calendarId='primary',
                eventId=event_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z'
            ).execute()

            for instance in instances.get('items', []):
                # Mark the instance as cancelled
                instance['status'] = 'cancelled'
                self.service.events().update(
                    calendarId='primary',
                    eventId=instance['id'],
                    body=instance
                ).execute()

            return True, f"Successfully cancelled {len(instances.get('items', []))} instances"

        except HttpError as error:
            return False, f"Failed to cancel meetings: {str(error)}"

    def send_cancellation_notifications(self, event: Dict, start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
        """
        Send cancellation notifications to all attendees of a recurring meeting.
        Returns a tuple of (success, message).
        """
        try:
            attendees = event.get('attendees', [])
            if not attendees:
                return True, "No attendees to notify"

            # Create the email message
            subject = f"Cancellation Notice: {event['summary']}"
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            body = f"""
            Hello,

            This is to inform you that the recurring meeting "{event['summary']}" 
            has been cancelled for the period from {start_str} to {end_str}.

            Original meeting details:
            {self.format_event_info(event)}

            Please update your calendar accordingly.

            Best regards,
            Calendar Assistant
            """

            # Create the email message in Gmail's required format
            message = MIMEText(body)
            message['to'] = ', '.join(a['email'] for a in attendees if 'email' in a)
            message['from'] = 'me'  # Gmail API uses 'me' to refer to the authenticated user
            message['subject'] = subject

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send the email
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return True, f"Successfully sent cancellation notifications to {len(attendees)} attendees"

        except Exception as error:
            return False, f"Failed to send notifications: {str(error)}"

    def cancel_recurring_meeting_with_notifications(
        self, 
        event_id: str, 
        start_date: datetime, 
        end_date: datetime,
        send_notifications: bool = True
    ) -> Dict[str, str]:
        """
        Cancel a recurring meeting and optionally send notifications to attendees.
        Returns a dictionary with status messages for both operations.
        """
        results = {}
        
        # First, get the event details
        try:
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
        except HttpError as error:
            return {'error': f"Failed to fetch event: {str(error)}"}

        # Cancel the meetings
        cancel_success, cancel_message = self.cancel_recurring_meetings(event_id, start_date, end_date)
        results['cancellation'] = cancel_message

        # Send notifications if requested and cancellation was successful
        if send_notifications and cancel_success:
            notif_success, notif_message = self.send_cancellation_notifications(event, start_date, end_date)
            results['notifications'] = notif_message

        return results

    def get_one_off_meetings(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get all one-off meetings in the specified date range.
        Returns a list of meeting dictionaries.
        """
        events = self.get_events(start_date, end_date)
        classified = self.classify_events(events)
        return classified['one_off']

    def generate_rescheduling_template(self, event: Dict, reason: str = "time off") -> str:
        """
        Generate an email template for rescheduling a one-off meeting.
        """
        start = event['start'].get('dateTime', event['start'].get('date'))
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        
        organizer = event.get('organizer', {}).get('email', 'the organizer')
        attendees = event.get('attendees', [])
        attendee_list = ', '.join(a['email'] for a in attendees if 'email' in a)
        
        template = f"""
Subject: Rescheduling Request: {event['summary']}

Dear {organizer},

I hope this email finds you well. I need to reschedule our meeting that is currently scheduled for {start_dt.strftime('%A, %B %d at %I:%M %p')} due to {reason}.

Meeting Details:
- Title: {event['summary']}
- Current Time: {start_dt.strftime('%Y-%m-%d %I:%M %p')}
- Attendees: {attendee_list if attendee_list else 'No other attendees'}

Would it be possible to reschedule this meeting? Please let me know what times work best for you.

Thank you for your understanding.

Best regards,
{self.get_authenticated_user_email()}
"""
        return template

    def send_rescheduling_email(self, event: Dict, custom_message: Optional[str] = None) -> Tuple[bool, str]:
        """
        Send a rescheduling email for a one-off meeting.
        Returns a tuple of (success, message).
        """
        try:
            if not custom_message:
                custom_message = self.generate_rescheduling_template(event)

            # Create the email message
            message = MIMEText(custom_message)
            
            # Get all recipient emails
            recipients = []
            if 'organizer' in event and 'email' in event['organizer']:
                recipients.append(event['organizer']['email'])
            for attendee in event.get('attendees', []):
                if 'email' in attendee:
                    recipients.append(attendee['email'])
            
            # Remove duplicates and the sender's email
            sender_email = self.get_authenticated_user_email()
            recipients = list(set(recipients))
            if sender_email in recipients:
                recipients.remove(sender_email)

            if not recipients:
                return False, "No recipients found for the email"

            message['to'] = ', '.join(recipients)
            message['from'] = 'me'
            message['subject'] = f"Rescheduling Request: {event['summary']}"

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send the email
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return True, f"Successfully sent rescheduling email to {len(recipients)} recipients"

        except Exception as error:
            return False, f"Failed to send rescheduling email: {str(error)}"

    def get_authenticated_user_email(self) -> str:
        """
        Get the email address of the authenticated user.
        """
        try:
            user_info_service = build('oauth2', 'v2', credentials=self.credentials)
            user_info = user_info_service.userinfo().get().execute()
            return user_info['email']
        except Exception:
            return "me"  # Fallback to 'me' if we can't get the email

    def handle_one_off_meeting(self, event: Dict, custom_message: Optional[str] = None) -> Dict[str, str]:
        """
        Handle a one-off meeting by generating/sending a rescheduling email.
        Returns a dictionary with status messages.
        """
        results = {
            'meeting_info': self.format_event_info(event)
        }

        if custom_message:
            results['template'] = custom_message
        else:
            results['template'] = self.generate_rescheduling_template(event)

        if custom_message is not None:  # Only send if custom_message is provided (None = don't send, '' = send with default template)
            success, message = self.send_rescheduling_email(event, custom_message)
            results['email_status'] = message

        return results

if __name__ == '__main__':
    # Test the calendar service
    calendar = CalendarService()
    
    # Get events for the next 7 days
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=7)
    
    # Get and display one-off meetings
    one_off_meetings = calendar.get_one_off_meetings(now, end)
    print(f"\nFound {len(one_off_meetings)} one-off meetings:")
    
    for meeting in one_off_meetings:
        print("\nMeeting details:")
        print(calendar.format_event_info(meeting))
        
        # Generate and display email template
        print("\nSuggested email template:")
        print(calendar.generate_rescheduling_template(meeting))
        print("-" * 80) 