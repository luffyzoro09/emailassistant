import os
import imaplib
import email
import smtplib
import time
from email.mime.text import MIMEText
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import requests
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential
from imapclient import IMAPClient
import email.utils
import traceback

# Load environment variables
print("Starting application...")
print("Current working directory:", os.getcwd())
env_path = os.path.join(os.getcwd(), ".env")
print("Loading .env from:", env_path)

# Read .env file directly
config = {}
try:
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
    print("Successfully loaded .env file")
except Exception as e:
    print(f"Error loading .env file: {e}")
    exit(1)

print("\nLoaded configuration:")
for key, value in config.items():
    if "PASS" in key or "KEY" in key:
        print(f"{key}: {'*' * len(value)}")
    else:
        print(f"{key}: {value}")

# Configuration
EMAIL_USER = config.get("EMAIL_USER")
EMAIL_PASS = config.get("EMAIL_PASS")
IMAP_SERVER = config.get("EMAIL_HOST", "imap.gmail.com")
SMTP_SERVER = config.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(config.get("SMTP_PORT", "587"))
IMAP_PORT = int(config.get("IMAP_PORT", "993"))
OLLAMA_MODEL = config.get("OLLAMA_MODEL", "mistral")

# Debug logging
print(f"\nConfiguration values:")
print(f"Using email user: {EMAIL_USER}")
print(f"Using IMAP server: {IMAP_SERVER}")
print(f"Using SMTP server: {SMTP_SERVER}")
print(f"Using Ollama model: {OLLAMA_MODEL}")
print(f"Password length: {len(EMAIL_PASS) if EMAIL_PASS else 0}")

if not EMAIL_USER or not EMAIL_PASS:
    print("Error: EMAIL_USER or EMAIL_PASS not found in environment variables")
    exit(1)

try:
    print("Initializing Ollama LLM...")
    # Initialize LangChain with Ollama
    llm = OllamaLLM(model=OLLAMA_MODEL, base_url="http://localhost:11434")
    print("Successfully initialized Ollama LLM")
except Exception as e:
    print(f"Error initializing Ollama LLM: {e}")
    print(traceback.format_exc())
    exit(1)

prompt = PromptTemplate(input_variables=["recipient_name", "email_body"],
                        template="""
                        You are writing a professional email response. Write a polite, formal response that maintains a professional tone.
                        Guidelines:
                        - Use proper business etiquette
                        - Be concise but thorough
                        - Avoid casual language, slang, or emojis
                        - Maintain a professional and respectful tone
                        - Use proper grammar and punctuation
                        - Keep the response focused and relevant to the original email
                        - Address the recipient by their name: {recipient_name}
                        - Format paragraphs properly:
                          * Start each paragraph with a clear topic sentence
                          * Keep paragraphs focused and well-structured
                          * Use proper spacing between paragraphs
                          * Ensure logical flow between ideas
                          * Left-align all text
                        
                        Original email:
                        {email_body}
                        
                        Your response:
                        """)

# Create a chain using the new pipe syntax
chain = prompt | llm

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_response_with_retry(email_body, recipient_name):
    """Generate an AI-powered response with retry logic."""
    try:
        # Check if Ollama server is running
        response = requests.get("http://localhost:11434/api/tags")
        response.raise_for_status()
        
        response = chain.invoke({
            "email_body": email_body,
            "recipient_name": recipient_name
        })
        return response.strip()
    except RequestException as e:
        print(f"Error connecting to Ollama server: {e}")
        raise
    except Exception as e:
        print(f"Error generating response: {e}")
        raise

def format_email_body(text):
    """Format the email body with proper HTML formatting."""
    # Split into paragraphs
    paragraphs = text.split('\n\n')
    
    # Format each paragraph with proper HTML
    formatted_paragraphs = []
    for para in paragraphs:
        if para.strip():  # Only process non-empty paragraphs
            # Replace single newlines with spaces
            para = ' '.join(para.split('\n'))
            # Add proper paragraph formatting
            formatted_paragraphs.append(f'<p style="margin: 0 0 1em 0; text-align: left;">{para}</p>')
    
    # Join paragraphs with proper spacing
    return '\n'.join(formatted_paragraphs)

def extract_name_from_email(from_header):
    """Extract name from email header."""
    try:
        name, email = email.utils.parseaddr(from_header)
        if name:
            # Remove any quotes and clean up the name
            name = name.strip('"\'')
            # If name contains email-like parts, return None
            if '@' in name:
                return None
            # Split name and take first part if multiple parts exist
            name_parts = name.split()
            if len(name_parts) > 1:
                return name_parts[0]  # Return first name only
            return name
        return None
    except:
        return None

def clean_subject(subject):
    """Clean the subject line by removing Re: and other prefixes."""
    if not subject:
        return "No Subject"
    # Remove common prefixes
    prefixes = ["Re:", "RE:", "Fwd:", "FWD:", "FW:", "fw:"]
    for prefix in prefixes:
        if subject.lower().startswith(prefix.lower()):
            subject = subject[len(prefix):].strip()
    return subject

def check_email():
    """Check inbox for unread emails."""
    try:
        print(f"Connecting to IMAP server {IMAP_SERVER}...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        print("Logging in...")
        mail.login(EMAIL_USER, EMAIL_PASS)
        print("Selecting inbox...")
        mail.select("inbox")
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        
        for email_id in email_ids:
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"]
                    from_header = msg["from"]
                    
                    # Extract recipient name
                    recipient_name = extract_name_from_email(from_header)
                    if not recipient_name:
                        # Try to get name from email address
                        _, email_addr = email.utils.parseaddr(from_header)
                        if email_addr:
                            recipient_name = email_addr.split('@')[0]
                        else:
                            recipient_name = "Recipient Name"
                    
                    # Extract email body
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                email_body = part.get_payload(decode=True).decode()
                                break
                    else:
                        email_body = msg.get_payload(decode=True).decode()
                    
                    print(f"New email from {from_header}: {subject}")
                    try:
                        reply = generate_response_with_retry(email_body, recipient_name)
                        clean_subject_line = clean_subject(subject)
                        formatted_reply = format_email_body(reply)
                        save_draft(from_header, clean_subject_line, formatted_reply)
                    except Exception as e:
                        print(f"Failed to process email after retries: {e}")
                        continue
    except Exception as e:
        print(f"Error checking email: {e}")
    finally:
        try:
            mail.logout()
        except:
            pass

def save_draft(to_email, subject, body):
    """Save response as a draft email."""
    try:
        print(f"Connecting to IMAP server to save draft...")
        with IMAPClient(IMAP_SERVER, port=IMAP_PORT, ssl=True) as client:
            client.login(EMAIL_USER, EMAIL_PASS)
            
            # Create the email message with HTML content
            msg = MIMEText(body, 'html')
            msg['Subject'] = subject  # Use the cleaned subject without "Re:"
            msg['From'] = EMAIL_USER
            msg['To'] = to_email
            
            # Select the Drafts folder
            client.select_folder('[Gmail]/Drafts')
            
            # Append the message as a draft
            client.append(
                folder='[Gmail]/Drafts',
                msg=msg.as_string(),
                flags=['\\Draft'],
                msg_time=None
            )
            print(f"Saved draft response for: {to_email}")
    except Exception as e:
        print(f"Error saving draft: {e}")

if __name__ == "__main__":
    while True:
        check_email()
        time.sleep(60)  # Check for new emails every 60 seconds