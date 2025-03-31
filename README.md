# Email Assistant Project

This project is an automated email assistant that uses Ollama and LangChain to generate professional email responses.

## Prerequisites

1. Python 3.8 or higher
2. Ollama installed and running locally (https://ollama.ai/)
3. Gmail account with App Password enabled

## Setup Instructions

1. Install Ollama:
   - Download and install from https://ollama.ai/
   - Start the Ollama service
   - Pull the Mistral model: `ollama pull mistral`

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Gmail:
   - Enable 2-factor authentication in your Gmail account
   - Generate an App Password:
     - Go to Google Account settings
     - Security
     - 2-Step Verification
     - App passwords
     - Generate a new app password for "Mail"

4. Update the `.env` file with your credentials:
   - EMAIL_USER: Your Gmail address
   - EMAIL_PASS: Your Gmail App Password
   - Other settings can remain as default

## Running the Application

1. Make sure Ollama is running locally
2. Run the application:
   ```bash
   python app.py
   ```

The application will:
- Check for new unread emails every 60 seconds
- Generate professional responses using Ollama
- Save responses as drafts in your Gmail account

## Notes

- The application uses the Mistral model by default
- Responses are saved as drafts for review before sending
- Make sure your Gmail account has sufficient storage space
- The application requires a stable internet connection 