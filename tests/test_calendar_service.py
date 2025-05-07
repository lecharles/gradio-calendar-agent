import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from src.calendar_service import CalendarService

class TestCalendarService(unittest.TestCase):
    def setUp(self):
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
        
        self.mock_instances = {
            'items': [
                {
                    'id': 'instance1',
                    'summary': 'Recurring Meeting',
                    'start': {'dateTime': '2024-05-06T10:00:00Z'},
                    'end': {'dateTime': '2024-05-06T11:00:00Z'},
                },
                {
                    'id': 'instance2',
                    'summary': 'Recurring Meeting',
                    'start': {'dateTime': '2024-05-13T10:00:00Z'},
                    'end': {'dateTime': '2024-05-13T11:00:00Z'},
                }
            ]
        }

    @patch('src.calendar_service.authenticate')
    @patch('src.calendar_service.build')
    def test_get_events(self, mock_build, mock_auth):
        # Setup mock calendar service
        mock_service = MagicMock()
        mock_events_obj = MagicMock()
        mock_events_obj.list().execute.return_value = {'items': self.mock_events}
        mock_service.events.return_value = mock_events_obj
        mock_build.return_value = mock_service

        # Create calendar service and get events
        calendar = CalendarService()
        start_date = datetime(2024, 5, 6)
        end_date = datetime(2024, 5, 7)
        events = calendar.get_events(start_date, end_date)

        # Verify results
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['summary'], 'Recurring Meeting')
        self.assertEqual(events[1]['summary'], 'One-off Meeting')

    def test_classify_events(self):
        calendar = CalendarService()
        classified = calendar.classify_events(self.mock_events)

        # Verify classification
        self.assertEqual(len(classified['recurring']), 1)
        self.assertEqual(len(classified['one_off']), 1)
        self.assertEqual(classified['recurring'][0]['summary'], 'Recurring Meeting')
        self.assertEqual(classified['one_off'][0]['summary'], 'One-off Meeting')

    def test_format_event_info(self):
        calendar = CalendarService()
        event_info = calendar.format_event_info(self.mock_events[0])

        # Verify formatting
        self.assertIn('Recurring Meeting', event_info)
        self.assertIn('test@example.com', event_info)
        self.assertIn('Recurring: Yes', event_info)

    @patch('src.calendar_service.authenticate')
    @patch('src.calendar_service.build')
    def test_cancel_recurring_meetings(self, mock_build, mock_auth):
        # Setup mock calendar service
        mock_service = MagicMock()
        mock_service.events().get().execute.return_value = self.mock_events[0]
        mock_service.events().instances().execute.return_value = self.mock_instances
        mock_service.events().update().execute.return_value = {}
        mock_build.return_value = mock_service

        # Create calendar service and cancel recurring meetings
        calendar = CalendarService()
        start_date = datetime(2024, 5, 6, tzinfo=timezone.utc)
        end_date = datetime(2024, 5, 20, tzinfo=timezone.utc)
        
        success, message = calendar.cancel_recurring_meetings('recurring123', start_date, end_date)
        
        # Verify results
        self.assertTrue(success)
        self.assertIn('Successfully cancelled 2 instances', message)
        
        # Verify the service calls
        mock_service.events().get.assert_called_with(calendarId='primary', eventId='recurring123')
        mock_service.events().instances.assert_called_with(
            calendarId='primary',
            eventId='recurring123',
            timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z'
        )

    @patch('src.calendar_service.authenticate')
    @patch('src.calendar_service.build')
    def test_send_cancellation_notifications(self, mock_build, mock_auth):
        # Setup mock services
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().send().execute.return_value = {}
        
        # Configure the build function to return different services
        def mock_build_service(service_name, version, credentials):
            if service_name == 'gmail':
                return mock_gmail_service
            return MagicMock()
        
        mock_build.side_effect = mock_build_service

        # Create calendar service and send notifications
        calendar = CalendarService()
        start_date = datetime(2024, 5, 6, tzinfo=timezone.utc)
        end_date = datetime(2024, 5, 20, tzinfo=timezone.utc)
        
        success, message = calendar.send_cancellation_notifications(self.mock_events[0], start_date, end_date)
        
        # Verify results
        self.assertTrue(success)
        self.assertIn('Successfully sent cancellation notifications to 1 attendees', message)
        
        # Verify the Gmail API was called
        self.assertTrue(mock_gmail_service.users().messages().send.called)

    @patch('src.calendar_service.authenticate')
    @patch('src.calendar_service.build')
    def test_cancel_recurring_meeting_with_notifications(self, mock_build, mock_auth):
        # Setup mock services
        mock_calendar_service = MagicMock()
        mock_gmail_service = MagicMock()
        
        # Configure calendar service mocks
        mock_calendar_service.events().get().execute.return_value = self.mock_events[0]
        mock_calendar_service.events().instances().execute.return_value = self.mock_instances
        mock_calendar_service.events().update().execute.return_value = {}
        
        # Configure Gmail service mocks
        mock_gmail_service.users().messages().send().execute.return_value = {}
        
        # Configure the build function to return different services
        def mock_build_service(service_name, version, credentials):
            if service_name == 'gmail':
                return mock_gmail_service
            return mock_calendar_service
        
        mock_build.side_effect = mock_build_service

        # Create calendar service and perform the combined operation
        calendar = CalendarService()
        start_date = datetime(2024, 5, 6, tzinfo=timezone.utc)
        end_date = datetime(2024, 5, 20, tzinfo=timezone.utc)
        
        results = calendar.cancel_recurring_meeting_with_notifications(
            'recurring123',
            start_date,
            end_date
        )
        
        # Verify results
        self.assertIn('Successfully cancelled 2 instances', results['cancellation'])
        self.assertIn('Successfully sent cancellation notifications', results['notifications'])
        
        # Verify both services were called
        mock_calendar_service.events().get.assert_called_with(calendarId='primary', eventId='recurring123')
        self.assertTrue(mock_gmail_service.users().messages().send.called)

    @patch('src.calendar_service.authenticate')
    @patch('src.calendar_service.build')
    def test_get_one_off_meetings(self, mock_build, mock_auth):
        # Setup mock calendar service
        mock_service = MagicMock()
        mock_events_obj = MagicMock()
        mock_events_obj.list().execute.return_value = {'items': self.mock_events}
        mock_service.events.return_value = mock_events_obj
        mock_build.return_value = mock_service

        # Create calendar service and get one-off meetings
        calendar = CalendarService()
        start_date = datetime(2024, 5, 6, tzinfo=timezone.utc)
        end_date = datetime(2024, 5, 20, tzinfo=timezone.utc)
        
        one_off_meetings = calendar.get_one_off_meetings(start_date, end_date)
        
        # Verify results
        self.assertEqual(len(one_off_meetings), 1)
        self.assertEqual(one_off_meetings[0]['summary'], 'One-off Meeting')
        self.assertNotIn('recurrence', one_off_meetings[0])

    def test_generate_rescheduling_template(self):
        calendar = CalendarService()
        template = calendar.generate_rescheduling_template(self.mock_events[1])
        
        # Verify template content
        self.assertIn('One-off Meeting', template)
        self.assertIn('May 07', template)
        self.assertIn('attendee1@example.com', template)
        self.assertIn('attendee2@example.com', template)
        self.assertIn('organizer@example.com', template)

    @patch('src.calendar_service.authenticate')
    @patch('src.calendar_service.build')
    def test_send_rescheduling_email(self, mock_build, mock_auth):
        # Setup mock services
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().send().execute.return_value = {}
        
        # Setup mock user info service
        mock_user_info_service = MagicMock()
        mock_user_info_service.userinfo().get().execute.return_value = {
            'email': 'me@example.com'
        }
        
        # Configure the build function to return different services
        def mock_build_service(service_name, version, credentials):
            if service_name == 'gmail':
                return mock_gmail_service
            elif service_name == 'oauth2':
                return mock_user_info_service
            return MagicMock()
        
        mock_build.side_effect = mock_build_service

        # Create calendar service and send rescheduling email
        calendar = CalendarService()
        custom_message = "Custom rescheduling message"
        success, message = calendar.send_rescheduling_email(self.mock_events[1], custom_message)
        
        # Verify results
        self.assertTrue(success)
        self.assertIn('Successfully sent rescheduling email', message)
        self.assertTrue(mock_gmail_service.users().messages().send.called)

    @patch('src.calendar_service.authenticate')
    @patch('src.calendar_service.build')
    def test_handle_one_off_meeting(self, mock_build, mock_auth):
        # Setup mock services
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().send().execute.return_value = {}
        
        mock_user_info_service = MagicMock()
        mock_user_info_service.userinfo().get().execute.return_value = {
            'email': 'me@example.com'
        }
        
        def mock_build_service(service_name, version, credentials):
            if service_name == 'gmail':
                return mock_gmail_service
            elif service_name == 'oauth2':
                return mock_user_info_service
            return MagicMock()
        
        mock_build.side_effect = mock_build_service

        # Create calendar service and handle one-off meeting
        calendar = CalendarService()
        
        # Test without sending email (custom_message = None)
        results = calendar.handle_one_off_meeting(self.mock_events[1])
        self.assertIn('meeting_info', results)
        self.assertIn('template', results)
        self.assertNotIn('email_status', results)
        
        # Test with custom message
        results = calendar.handle_one_off_meeting(self.mock_events[1], "Custom message")
        self.assertIn('meeting_info', results)
        self.assertIn('template', results)
        self.assertIn('email_status', results)
        self.assertIn('Successfully sent', results['email_status'])

if __name__ == '__main__':
    unittest.main() 