import os
import logging
import traceback
from .app import demo  # Import the demo interface directly from app.py

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler('meeting_rescheduler.log')  # Log to file
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Meeting Rescheduler application."""
    try:
        # Check for credentials file
        if not os.path.exists('credentials.json'):
            logger.error("credentials.json not found. Please obtain OAuth2 credentials from Google Cloud Console.")
            print(
                "Error: credentials.json not found!\n"
                "Please follow these steps:\n"
                "1. Go to Google Cloud Console\n"
                "2. Create a project or select an existing one\n"
                "3. Enable the Gmail and Calendar APIs\n"
                "4. Create OAuth2 credentials\n"
                "5. Download the credentials and save as 'credentials.json' in this directory"
            )
            return

        # Launch the full interface
        logger.info("Starting Meeting Rescheduler Assistant...")
        print("Attempting to launch interface on port 7860...")
        
        try:
            demo.launch(
                server_name="0.0.0.0",  # Listen on all network interfaces
                server_port=7860,  # Use port 7860 to match app.py
                share=False  # Don't create a public link
            )
            logger.info("Interface started successfully")
        except Exception as launch_error:
            if "Address already in use" in str(launch_error):
                logger.error("Port 7860 is already in use. Please ensure no other Gradio apps are running.")
                print("\nError: Port 7860 is already in use!")
                print("Please check if:\n1. Another instance is already running\n2. The port is being used by another application")
            else:
                logger.error(f"Failed to launch interface: {str(launch_error)}")
                print(f"Launch Error Details:\n{traceback.format_exc()}")
            raise

    except Exception as error:
        logger.error(f"Failed to start application: {str(error)}")
        print(f"Error Details:\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main() 