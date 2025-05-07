import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from src.chatbot import MeetingReschedulerBot

class TestMeetingReschedulerBot(unittest.TestCase):
    def setUp(self):
        self.bot = MeetingReschedulerBot()
        self.mock_events = [
            {
                'id': 'recurring123',
                'summary': 'Recurring Meeting',
                'start': {'dateTime': '2024-05-06T10:00:00Z'},
                'end': {'dateTime': '2024-05-06T11:00:00Z'},
                'recurrence': ['RRULE:FREQ=WEEKLY'],
                'attendees': [{'email': 'test@example.com'}],
                'organizer': {'email': 'organizer@example.com'}
            },
            {
                'id': 'oneoff456',
                'summary': 'One-off Meeting',
                'start': {'dateTime': '2024-05-07T14:00:00Z'},
                'end': {'dateTime': '2024-05-07T15:00:00Z'},
                'attendees': [
                    {'email': 'attendee1@example.com'},
                    {'email': 'attendee2@example.com'}
                ],
                'organizer': {'email': 'organizer@example.com'}
            }
        ]

    @patch('src.chatbot.CalendarService')
    def test_initialize_calendar_service(self, mock_calendar_service):
        # Test successful initialization
        response, state = self.bot.initialize_calendar_service()
        self.assertTrue(state['authenticated'])
        self.assertIn("Successfully authenticated", response)
        self.assertIn("YYYY-MM-DD to YYYY-MM-DD", response)

        # Test failed initialization
        mock_calendar_service.side_effect = Exception("Auth failed")
        bot = MeetingReschedulerBot()
        response, state = bot.initialize_calendar_service()
        self.assertFalse(state['authenticated'])
        self.assertIn("Authentication failed", response)

    def test_parse_date_range(self):
        # Test valid date range
        start_date, end_date = self.bot.parse_date_range("2024-05-01 to 2024-05-10")
        self.assertEqual(start_date.year, 2024)
        self.assertEqual(start_date.month, 5)
        self.assertEqual(start_date.day, 1)
        self.assertEqual(end_date.year, 2024)
        self.assertEqual(end_date.month, 5)
        self.assertEqual(end_date.day, 10)

        # Test invalid date range
        start_date, end_date = self.bot.parse_date_range("invalid date range")
        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

    @patch('src.chatbot.CalendarService')
    def test_process_time_off_dates(self, mock_calendar_service):
        # Setup mock calendar service
        mock_instance = mock_calendar_service.return_value
        mock_instance.get_events.return_value = self.mock_events
        mock_instance.classify_events.return_value = {
            'recurring': [self.mock_events[0]],
            'one_off': [self.mock_events[1]]
        }

        # Test without authentication
        response, state = self.bot.process_time_off_dates("2024-05-01 to 2024-05-10")
        self.assertIn("Please authenticate first", response)

        # Test with authentication
        self.bot.state['authenticated'] = True
        response, state = self.bot.process_time_off_dates("2024-05-01 to 2024-05-10")
        self.assertIn("Found 2 meetings", response)
        self.assertIn("1 recurring meetings", response)
        self.assertIn("1 one-off meetings", response)

        # Test invalid date format
        response, state = self.bot.process_time_off_dates("invalid date range")
        self.assertIn("Invalid date format", response)

        # Test end date before start date
        response, state = self.bot.process_time_off_dates("2024-05-10 to 2024-05-01")
        self.assertIn("End date must be after start date", response)

    @patch('src.chatbot.CalendarService')
    def test_handle_recurring_meetings(self, mock_calendar_service):
        # Setup mock calendar service
        mock_instance = mock_calendar_service.return_value
        mock_instance.cancel_recurring_meeting_with_notifications.return_value = {
            'cancellation': 'Successfully cancelled 1 instance',
            'notifications': 'Successfully sent notifications'
        }

        # Setup state
        self.bot.state['authenticated'] = True
        self.bot.state['recurring_meetings'] = [self.mock_events[0]]
        self.bot.state['one_off_meetings'] = [self.mock_events[1]]
        self.bot.calendar_service = mock_instance

        # Test invalid input
        response, state = self.bot.handle_recurring_meetings("maybe")
        self.assertIn("Please answer 'yes' or 'no'", response)

        # Test declining cancellation
        response, state = self.bot.handle_recurring_meetings("no")
        self.assertIn("Would you like to review the one-off meetings?", response)

        # Test accepting cancellation
        response, state = self.bot.handle_recurring_meetings("yes")
        self.assertIn("Recurring meetings handled", response)
        self.assertIn("Successfully cancelled 1 instance", response)
        self.assertIn("Successfully sent notifications", response)

    @patch('src.chatbot.CalendarService')
    def test_handle_one_off_meetings(self, mock_calendar_service):
        # Setup mock calendar service
        mock_instance = mock_calendar_service.return_value
        mock_instance.format_event_info.return_value = "Meeting details"
        mock_instance.generate_rescheduling_template.return_value = "Email template"
        mock_instance.handle_one_off_meeting.return_value = {
            'meeting_info': 'Meeting details',
            'template': 'Email template',
            'email_status': 'Successfully sent'
        }

        # Setup state
        self.bot.state['authenticated'] = True
        self.bot.state['one_off_meetings'] = [self.mock_events[1]]
        self.bot.calendar_service = mock_instance

        # Test initial prompt
        response, state = self.bot.handle_one_off_meetings("yes")
        self.assertIn("Let's review the one-off meetings", response)
        self.assertIn("Meeting details", response)
        self.assertIn("Email template", response)

        # Test sending email
        response, state = self.bot.handle_one_off_meetings("send")
        self.assertIn("Email sent successfully", response)
        self.assertIn("All meetings have been handled", response)

        # Test skipping meeting
        self.bot.state['current_meeting_index'] = 0
        response, state = self.bot.handle_one_off_meetings("skip")
        self.assertIn("Meeting skipped", response)

        # Test editing template
        self.bot.state['current_meeting_index'] = 0
        response, state = self.bot.handle_one_off_meetings("edit")
        self.assertIn("Please enter your customized email message", response)

        # Test custom template
        response, state = self.bot.handle_one_off_meetings("Custom email content")
        self.assertIn("Email template updated", response)

    @patch('src.chatbot.CalendarService')
    def test_chat(self, mock_calendar_service):
        # Test initial authentication
        response, state = self.bot.chat("", [], None)
        self.assertIn("Successfully authenticated", response)

        # Test date processing
        self.bot.state['authenticated'] = True
        response, state = self.bot.chat("2024-05-01 to 2024-05-10", [], self.bot.state)
        self.assertIn("Found", response)

        # Test recurring meetings
        self.bot.state['recurring_meetings'] = [self.mock_events[0]]
        response, state = self.bot.chat("yes", [], self.bot.state)
        self.assertIn("Recurring meetings handled", response)

        # Test one-off meetings
        self.bot.state['one_off_meetings'] = [self.mock_events[1]]
        self.bot.state['current_meeting_index'] = 0
        response, state = self.bot.chat("yes", [], self.bot.state)
        self.assertIn("Let's review the one-off meetings", response)

if __name__ == '__main__':
    unittest.main() 