import os
import sys
from meeting_rescheduler.calendar_tool import CalendarTool
from dotenv import load_dotenv

# Redirect output to a file
with open('test_output.log', 'w') as f:
    def log(msg):
        f.write(msg + '\n')
        f.flush()
    
    log("Starting test script...")
    log(f"Current directory: {os.getcwd()}")
    
    # Load environment variables
    load_dotenv()
    log("Environment variables loaded")
    
    try:
        # Create calendar tool
        log("Creating calendar tool...")
        tool = CalendarTool()
        log("Calendar tool created")
        
        # Test authentication
        log("Testing calendar authentication...")
        log(f"credentials.json exists: {os.path.exists('credentials.json')}")
        assert os.path.exists('credentials.json'), "credentials.json not found"
        
        success = tool.authenticate()
        log(f"Authentication result: {success}")
        assert success, "Calendar authentication failed"
        assert tool.calendar_service is not None, "Calendar service is None"
        assert tool.gmail_service is not None, "Gmail service is None"
        log("Calendar authentication test completed successfully")
    except Exception as e:
        log(f"Error occurred: {str(e)}")
        sys.exit(1) 