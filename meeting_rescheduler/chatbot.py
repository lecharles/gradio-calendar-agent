"""
Gradio chatbot interface for the Meeting Rescheduler Agent.
"""

import os
import gradio as gr
from typing import List, Tuple
from .llm.conversation import ConversationManager
from .calendar_service import CalendarService

class MeetingReschedulerBot:
    def __init__(self, openai_api_key: str = None):
        """Initialize the chatbot interface.
        
        Args:
            openai_api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY env var.
        """
        self.conversation = ConversationManager(api_key=openai_api_key)
        self.calendar_service = None
    
    async def chat(self, message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
        """Process a chat message and return the response.
        
        Args:
            message: The user's message
            history: The chat history
            
        Returns:
            Tuple of (bot response, updated history)
        """
        try:
            # Get response from LLM
            response, state = await self.conversation.get_response(message)
            
            # Handle any calendar operations based on state
            if state.get('current_action') == 'authenticate' and not state.get('authenticated'):
                # Initialize calendar service if needed
                if not self.calendar_service:
                    self.calendar_service = CalendarService()
                    state['authenticated'] = True
            
            elif state.get('current_action') == 'get_meetings' and state.get('authenticated'):
                # Fetch meetings if time period is set
                if state.get('time_off_start') and state.get('time_off_end'):
                    events = self.calendar_service.get_events(
                        start_date=state['time_off_start'],
                        end_date=state['time_off_end']
                    )
                    # Classify and store events
                    recurring, one_off = self.calendar_service.classify_events(events)
                    for event in recurring:
                        self.conversation.state_manager.add_calendar_event(event, is_recurring=True)
                    for event in one_off:
                        self.conversation.state_manager.add_calendar_event(event, is_recurring=False)
            
            elif state.get('current_action') == 'cancel_recurring':
                # Handle recurring meeting cancellations
                for meeting in state.get('recurring_meetings', []):
                    if meeting.status == 'pending':
                        self.calendar_service.cancel_recurring_meeting(meeting.event_id)
                        self.conversation.state_manager.update_meeting_status(
                            meeting.event_id,
                            'cancelled'
                        )
            
            elif state.get('current_action') == 'send_emails':
                # Handle email sending for one-off meetings
                for meeting in state.get('one_off_meetings', []):
                    if meeting.status == 'pending':
                        template = self.conversation.templates.get_email_template('one_off')
                        self.calendar_service.send_rescheduling_email(
                            meeting.event_id,
                            template,
                            meeting.attendees
                        )
                        self.conversation.state_manager.update_meeting_status(
                            meeting.event_id,
                            'notified'
                        )
            
            return response, self.conversation.get_history()
            
        except Exception as error:
            error_message = f"An error occurred: {str(error)}"
            self.conversation.state_manager.set_error(error_message)
            return error_message, self.conversation.get_history()
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface.
        
        Returns:
            Gradio Blocks interface
        """
        with gr.Blocks() as interface:
            chatbot = gr.Chatbot(
                label="Meeting Rescheduler Assistant",
                height=600
            )
            msg = gr.Textbox(
                label="Type your message here...",
                placeholder="How can I help you manage your calendar today?",
                lines=2
            )
            clear = gr.Button("Clear Conversation")
            
            msg.submit(
                self.chat,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot]
            )
            
            clear.click(
                lambda: ([], []),
                outputs=[msg, chatbot],
                queue=False
            ).then(
                lambda: self.conversation.clear_history()
            )
        
        return interface

def create_chatbot(openai_api_key: str = None) -> gr.Blocks:
    """Create and return a new chatbot interface.
    
    Args:
        openai_api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY env var.
        
    Returns:
        Gradio Blocks interface
    """
    bot = MeetingReschedulerBot(openai_api_key=openai_api_key)
    return bot.create_interface()
