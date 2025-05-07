"""
Prompt templates for the Meeting Rescheduler Agent.
Manages system prompts and state-specific prompts.
"""

from typing import Dict
import json

class PromptTemplates:
    def get_system_prompt(self) -> str:
        """Get the system prompt that defines the agent's behavior."""
        return """You are a helpful meeting rescheduler assistant. Your role is to help users manage their calendar during time off periods.

Your capabilities include:
1. Authenticating with Google Calendar
2. Getting time off dates from users
3. Managing recurring meetings (cancelling them)
4. Handling one-off meetings (sending personalized emails)
5. Maintaining context throughout the conversation

Always:
- Be professional and courteous
- Confirm before making any calendar changes
- Keep track of the current state
- Handle errors gracefully
- Provide clear status updates

Never:
- Make assumptions about dates or times
- Modify calendar events without explicit confirmation
- Send emails without user approval
- Share sensitive calendar information

Start by asking how you can help with calendar management today."""

    def get_state_prompt(self, state: Dict) -> str:
        """Get a prompt that includes the current conversation state.
        
        Args:
            state: Current conversation state dictionary
            
        Returns:
            A prompt string that includes relevant state information
        """
        # Convert state to a readable format
        state_summary = []
        
        if state.get('authenticated'):
            state_summary.append("✓ User is authenticated")
        else:
            state_summary.append("⨯ User needs to authenticate")
            
        if state.get('time_off_start') and state.get('time_off_end'):
            state_summary.append(
                f"Time off period: {state['time_off_start']} to {state['time_off_end']}"
            )
            
        if state.get('recurring_meetings'):
            count = len(state['recurring_meetings'])
            state_summary.append(f"Found {count} recurring meetings")
            
        if state.get('one_off_meetings'):
            count = len(state['one_off_meetings'])
            state_summary.append(f"Found {count} one-off meetings")
            
        if state.get('current_action'):
            state_summary.append(f"Current action: {state['current_action']}")
            
        if state.get('last_error'):
            state_summary.append(f"Last error: {state['last_error']}")
        
        # Create the state-aware prompt
        prompt = f"""Current State:
{chr(10).join(f'- {item}' for item in state_summary)}

Remember this state while responding to the user. Guide them through any incomplete steps and help them accomplish their goal of managing calendar events during their time off."""
        
        return prompt
    
    def get_email_template(self, meeting_type: str) -> str:
        """Get an email template for a specific meeting type.
        
        Args:
            meeting_type: Type of meeting ('recurring' or 'one_off')
            
        Returns:
            An email template string
        """
        templates = {
            'recurring': """Subject: Cancellation Notice: {meeting_name}

Hi {attendee_name},

I hope this email finds you well. I wanted to let you know that I'll be taking some time off from {time_off_start} to {time_off_end}, and as a result, our recurring meeting "{meeting_name}" will be cancelled during this period.

We can resume our regular schedule when I return.

Best regards,
{user_name}""",
            
            'one_off': """Subject: Unable to Attend: {meeting_name}

Hi {attendee_name},

I hope you're doing well. I wanted to let you know that I'll be unavailable for our scheduled meeting "{meeting_name}" on {meeting_date} as I will be taking some time off.

Would it be possible to reschedule this meeting for after my return on {time_off_end}?

Best regards,
{user_name}"""
        }
        
        return templates.get(meeting_type, "") 