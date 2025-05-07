import os
import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Tuple, Dict, Any
from datetime import datetime, timedelta
import re
import json
from .calendar_tool import CalendarTool

# Load environment variables
load_dotenv()

# Initialize OpenAI client with error handling
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

try:
    client = OpenAI(api_key=api_key)
    calendar_tool = CalendarTool()
except Exception as e:
    print(f"Error initializing services: {e}")
    raise

# Global state for connection status
is_connected = False

def connect_calendar():
    """Connect to Google Calendar."""
    global is_connected
    try:
        if calendar_tool.authenticate():
            is_connected = True
            status_msg = "✅ Successfully connected to Google Calendar!"
            chatbot_msg = status_msg
            # Try to get upcoming events as a test
            try:
                _, events = calendar_tool.get_upcoming_events_count(7)
                if events:
                    chatbot_msg += "\n\nFound your calendar! Here are your upcoming meetings:\n\n"
                    chatbot_msg += format_events_message(events)
            except Exception as e:
                print(f"Error getting initial events: {e}")
            return status_msg, chatbot_msg
        error_msg = "❌ Failed to connect to Google Calendar. Please check your credentials."
        return error_msg, error_msg
    except Exception as e:
        error_msg = str(e)
        if "credentials.json" in error_msg:
            error_msg = "❌ Error: credentials.json not found. Please ensure you have your Google OAuth credentials file."
        else:
            error_msg = f"❌ Error connecting to calendar: {error_msg}"
        return error_msg, error_msg

def get_events_for_range(start_date: str, end_date: str) -> str:
    """Get events for a specific date range."""
    if not is_connected:
        return "Please connect to Google Calendar first."
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        events = calendar_tool.get_events(start, end)
        return format_events_message(events)
    except Exception as e:
        return f"Error retrieving events: {str(e)}"

def cancel_event_by_id(event_id: str) -> str:
    """Cancel a specific event."""
    if not is_connected:
        return "Please connect to Google Calendar first."
    
    try:
        if calendar_tool.cancel_event(event_id.strip()):
            return f"✅ Successfully cancelled event {event_id}"
        return f"❌ Failed to cancel event {event_id}"
    except Exception as e:
        return f"❌ Error cancelling event: {str(e)}"

def send_reschedule_email(event_id: str, message: str) -> str:
    """Send a rescheduling email for a specific event."""
    if not is_connected:
        return "Please connect to Google Calendar first."
    
    try:
        event = calendar_tool.get_event_details(event_id.strip())
        if event and calendar_tool.send_rescheduling_email(event, message):
            return f"✅ Successfully sent rescheduling email for event {event_id}"
        return f"❌ Failed to send rescheduling email for event {event_id}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

def format_events_message(events: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format events into a readable message with markdown."""
    message = "## Your Meetings\n\n"
    
    if events['recurring']:
        message += "### 🔄 Recurring Meetings\n"
        for event in events['recurring']:
            start_time = event.get('start', {}).get('dateTime', 'unknown time')
            if isinstance(start_time, str):
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.strftime('%B %d, %Y at %I:%M %p')
                except:
                    pass
            message += f"- **{event.get('summary', 'Untitled')}**\n"
            message += f"  - Time: {start_time}\n"
            message += f"  - ID: `{event['id']}`\n"
            if event.get('attendees'):
                message += f"  - Attendees: {len(event['attendees'])}\n"
            message += "\n"
    
    if events['one_off']:
        message += "### 📅 One-off Meetings\n"
        for event in events['one_off']:
            start_time = event.get('start', {}).get('dateTime', 'unknown time')
            if isinstance(start_time, str):
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.strftime('%B %d, %Y at %I:%M %p')
                except:
                    pass
            message += f"- **{event.get('summary', 'Untitled')}**\n"
            message += f"  - Time: {start_time}\n"
            message += f"  - ID: `{event['id']}`\n"
            if event.get('attendees'):
                message += f"  - Attendees: {len(event['attendees'])}\n"
            message += "\n"
    
    if not events['recurring'] and not events['one_off']:
        message += "_No meetings found in this time period._\n"
    
    return message

def parse_date_range(text: str) -> Tuple[datetime, datetime]:
    """Extract date range from user input using GPT-4."""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts date ranges from text. Always respond with exactly two dates in YYYY-MM-DD format, separated by a newline. If no specific dates are mentioned, use the next occurrence of the time period mentioned."},
                {"role": "user", "content": text}
            ],
            temperature=0
        )
        
        dates = response.choices[0].message.content.strip().split('\n')
        if len(dates) != 2:
            raise ValueError("Expected exactly two dates in response")
            
        start = datetime.strptime(dates[0], '%Y-%m-%d')
        end = datetime.strptime(dates[1], '%Y-%m-%d')
        return start, end
    except Exception as e:
        print(f"Error parsing dates: {e}")
        # Return next week as default
        start = datetime.now()
        end = start + timedelta(days=7)
        return start, end

def parse_event_datetime(text: str) -> Tuple[datetime, datetime]:
    """Extract specific event date and time from text using GPT-4."""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts event date and time from text. Always respond with exactly two lines in YYYY-MM-DD HH:MM format for start and end time. If only start time is mentioned, assume 1 hour duration. If no specific time is mentioned, use 10:00 AM. If no date is mentioned, use the next business day."},
                {"role": "user", "content": text}
            ],
            temperature=0
        )
        
        times = response.choices[0].message.content.strip().split('\n')
        if len(times) != 2:
            raise ValueError("Expected start and end time")
            
        start = datetime.strptime(times[0], '%Y-%m-%d %H:%M')
        end = datetime.strptime(times[1], '%Y-%m-%d %H:%M')
        return start, end
    except Exception as e:
        print(f"Error parsing event time: {e}")
        # Default to next business day at 10 AM
        start = datetime.now().replace(hour=10, minute=0) + timedelta(days=1)
        if start.weekday() > 4:  # If weekend, move to Monday
            start += timedelta(days=(7 - start.weekday()))
        return start, start + timedelta(hours=1)

def extract_event_details(text: str) -> Dict[str, Any]:
    """Extract event details from text using GPT-4."""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts event details from text. Return a JSON object with: summary (string), description (string), location (string), and attendees (array of email addresses). If any field is not mentioned, use empty string or empty array."},
                {"role": "user", "content": text}
            ],
            temperature=0
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error extracting event details: {e}")
        return {
            "summary": "New Meeting",
            "description": "",
            "location": "",
            "attendees": []
        }

def chat_with_gpt(message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
    """Process user input and generate response using GPT-4."""
    try:
        if not message.strip():
            return "", history
            
        # Check for calendar connection request
        if "connect" in message.lower() and "calendar" in message.lower():
            response = connect_calendar()
            return "", history + [[message, response]]
            
        # Check if calendar is connected before proceeding with other operations
        if not is_connected:
            if any(phrase in message.lower() for phrase in [
                "schedule", "create", "cancel", "upcoming", "meetings", "events"
            ]):
                return "", history + [[message, "Please connect to Google Calendar first by saying 'connect calendar'"]]
        
        # Check for upcoming events query
        if any(phrase in message.lower() for phrase in ["how many meetings", "upcoming events", "upcoming meetings", "schedule for next"]):
            days_match = re.search(r'next\s+(\d+)\s+days?', message.lower())
            days = int(days_match.group(1)) if days_match else 7
            
            count, events = calendar_tool.get_upcoming_events_count(days)
            events_message = format_events_message(events)
            response = f"You have {count} upcoming meetings in the next {days} days.\n\n{events_message}"
            return "", history + [[message, response]]
        
        # Check for event creation request
        if any(phrase in message.lower() for phrase in ["schedule a meeting", "create an event", "set up a meeting", "arrange a meeting"]):
            # Extract event details and time
            details = extract_event_details(message)
            start_time, end_time = parse_event_datetime(message)
            
            # Create the event
            event = calendar_tool.create_event(
                summary=details["summary"],
                start_time=start_time,
                end_time=end_time,
                description=details["description"],
                location=details["location"],
                attendees=details["attendees"]
            )
            
            if event:
                response = f"✅ I've created the event:\n\n" + \
                          f"**{event.get('summary')}**\n" + \
                          f"📅 {start_time.strftime('%B %d, %Y at %I:%M %p')} to {end_time.strftime('%I:%M %p')}\n"
                if event.get('location'):
                    response += f"📍 {event['location']}\n"
                if event.get('attendees'):
                    response += f"👥 {len(event['attendees'])} attendees\n"
                response += f"\nEvent ID: `{event['id']}`"
            else:
                response = "❌ Sorry, I couldn't create the event. Please try again with more specific details."
            return "", history + [[message, response]]
        
        # Check for event cancellation request
        if "cancel" in message.lower() and ("event" in message.lower() or "meeting" in message.lower()):
            event_id_match = re.search(r'ID:?\s*([^\s]+)', message)
            if event_id_match:
                event_id = event_id_match.group(1)
                response = cancel_event_by_id(event_id)
                return "", history + [[message, response]]
            else:
                response = "Please provide the event ID to cancel. You can find event IDs by asking about your upcoming meetings."
                return "", history + [[message, response]]
        
        # Check for time off or vacation related queries
        if any(phrase in message.lower() for phrase in ["time off", "vacation", "away", "out of office"]):
            start_date, end_date = parse_date_range(message)
            events = calendar_tool.get_events(start_date, end_date)
            response = format_events_message(events)
            return "", history + [[message, response]]
            
        # Default to regular chat
        messages = [{"role": "system", "content": """You are a helpful meeting rescheduler assistant that helps users manage their calendar. You can:
1. Create new events (e.g., 'schedule a meeting with John tomorrow at 2pm')
2. Show upcoming events (e.g., 'what meetings do I have next week?')
3. Cancel events (e.g., 'cancel the meeting with ID:xyz')
4. Handle time off periods (e.g., 'I'll be on vacation next week')
If users don't provide enough details, ask for clarification."""}]
        
        # Convert history to OpenAI message format
        for human, assistant in history:
            if human:
                messages.append({"role": "user", "content": human})
            if assistant:
                messages.append({"role": "assistant", "content": assistant})
        
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        bot_message = response.choices[0].message.content
        return "", history + [[message, bot_message]]
    except Exception as e:
        error_message = f"❌ I apologize, but I encountered an error: {str(e)}"
        print(f"Error in chat_with_gpt: {e}")
        return "", history + [[message, error_message]]

# Create the Gradio interface with the enhanced configuration
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📅 Meeting Rescheduler Assistant")
    gr.Markdown("I can help you manage your calendar during your time off. Let me know what you'd like to do!")
    
    with gr.Row():
        connect_btn = gr.Button("🔗 Connect Calendar", variant="primary")
        status = gr.Textbox(label="Connection Status", interactive=False)
    
    with gr.Row():
        with gr.Column():
            start_date = gr.Textbox(
                label="Start Date (YYYY-MM-DD)",
                placeholder="2024-05-01",
                type="text"
            )
            end_date = gr.Textbox(
                label="End Date (YYYY-MM-DD)",
                placeholder="2024-05-07",
                type="text"
            )
            get_events_btn = gr.Button("🔍 Get Events", variant="secondary")
    
    with gr.Row():
        with gr.Column():
            event_id = gr.Textbox(
                label="Event ID",
                placeholder="Enter event ID to cancel or send email",
                type="text"
            )
            email_message = gr.Textbox(
                label="Email Message",
                placeholder="Optional: Enter message for rescheduling email",
                type="text",
                lines=3
            )
            with gr.Row():
                cancel_btn = gr.Button("❌ Cancel Event", variant="stop")
                email_btn = gr.Button("📧 Send Email", variant="secondary")
    
    chatbot = gr.Chatbot(
        value=[],
        render_markdown=True,
        avatar_images=("👤", "🤖"),
        height=400
    )
    msg = gr.Textbox(
        placeholder="Type your message here...",
        label="Your message",
        autofocus=True
    )
    clear = gr.ClearButton([msg, chatbot], value="🗑️ Clear")
    
    # Set up event handlers
    connect_btn.click(
        connect_calendar,
        outputs=[status, chatbot],
        show_progress=True
    )
    get_events_btn.click(
        get_events_for_range,
        inputs=[start_date, end_date],
        outputs=chatbot
    )
    cancel_btn.click(
        cancel_event_by_id,
        inputs=[event_id],
        outputs=chatbot
    )
    email_btn.click(
        send_reschedule_email,
        inputs=[event_id, email_message],
        outputs=chatbot
    )
    msg.submit(
        chat_with_gpt,
        [msg, chatbot],
        [msg, chatbot]
    )
    
    with gr.Accordion("ℹ️ Examples", open=False):
        examples = gr.Examples(
            examples=[
                "I need to take next week off. Can you help me manage my meetings?",
                "Can you help me cancel my recurring meetings for the next two weeks?",
                "Schedule a meeting with john@example.com tomorrow at 2 PM titled 'Project Review'",
                "What meetings do I have next week?",
                "Cancel the meeting with ID: [paste event ID here]",
                "Send a rescheduling email for meeting ID: [paste event ID here]"
            ],
            inputs=msg
        )

if __name__ == "__main__":
    print("Starting Meeting Rescheduler Assistant...")
    demo.launch(share=False, server_name="0.0.0.0", server_port=7860)