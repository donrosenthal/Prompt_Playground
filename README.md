# Prompt Playground

A web-based tool for testing LLM prompts with real Gmail data. Built to help developers and AI engineers experiment with different prompts against actual email content, making it easier to develop and debug email processing workflows.

## Features

- **Gmail Integration**: Fetch real emails from your Gmail account by date
- **Interactive Email List**: Browse and select from all fetched emails in a sidebar
- **LLM Chat Interface**: Test prompts against selected email content
- **Streaming Responses**: Real-time LLM responses via Server-Sent Events
- **Email Context Injection**: Automatically includes email body, sender, subject, and date in your queries
- **Conversation History**: Maintains chat context across multiple queries
- **Timezone-Aware**: Correctly displays email timestamps in your local timezone

## Use Cases

- Developing email classification prompts
- Testing email summarization approaches
- Debugging email parsing logic
- Prototyping email automation workflows
- Experimenting with different LLM models for email tasks

## Prerequisites

- Python 3.8+
- Gmail account with API access enabled
- Google Cloud Console project with Gmail API enabled
- OAuth 2.0 credentials for Gmail API
- Anthropic API key for Claude

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Prompt_Playground.git
cd Prompt_Playground
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Gmail API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the credentials file and save it as `credentials.json` in the project root

### 5. Set Up Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Usage

### Starting the Server

```bash
python ui_Chatbot_prototype.py
```

The server will start on `http://localhost:8000`

### First Run - Gmail Authentication

On your first run, the application will:
1. Open your browser for Gmail OAuth authorization
2. Ask you to grant permissions to read Gmail messages
3. Create a `token.json` file to store your credentials

**Important**: Keep `credentials.json` and `token.json` secure and never commit them to version control.

### Using the Interface

1. **Fetch Emails**:
   - Select a date using the date picker in the sidebar
   - Click "Fetch" to retrieve emails from that date
   - All email metadata (sender, subject, date) will appear in a scrollable list

2. **Select an Email**:
   - Click any email in the list to select it
   - The email body is fetched on-demand (lazy loading)
   - Selected email is highlighted in blue

3. **Query with Context**:
   - Type your prompt in the text area
   - The selected email's full content is automatically injected into your query
   - LLM responses stream in real-time

4. **Clear Conversation**:
   - Click "Clear Conversation" to reset the chat history
   - Email list and selection persist

## Architecture

### Backend

- [ui_Chatbot_prototype.py](ui_Chatbot_prototype.py) - Simple HTTP server with SSE support
- [handlers/ui_handler_functions.py](handlers/ui_handler_functions.py) - API endpoint handlers
- [V0.4.py](V0.4.py) - Gmail integration module with OAuth and API calls

### Frontend

- [chatbot.html](chatbot.html) - Main UI structure with sidebar and chat area
- [script.js](script.js) - Client-side logic for email list, selection, and chat
- [styles.css](styles.css) - Responsive styling with Gmail-inspired email list

### Key Design Decisions

1. **Lazy Loading**: Email bodies are only fetched when user clicks an email, keeping initial load fast
2. **Timezone Handling**: Uses Gmail's `internal_date` (Unix timestamp) and converts to local time, ensuring accurate display and sorting
3. **Email Context Injection**: Full email content is prepended to user queries automatically, making it seamless to test prompts
4. **Server-Sent Events**: Enables real-time streaming of LLM responses for better UX

## File Structure

```
Prompt_Playground/
├── ui_Chatbot_prototype.py       # Main server
├── V0.4.py                        # Gmail integration module
├── chatbot.html                   # UI template
├── script.js                      # Frontend JavaScript
├── styles.css                     # Styling
├── handlers/
│   └── ui_handler_functions.py   # API endpoint handlers
├── credentials.json               # Gmail OAuth credentials (gitignored)
├── token.json                     # OAuth tokens (gitignored)
├── .env                           # Environment variables (gitignored)
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Gmail API Scopes

The application requests the following Gmail API scope:
- `https://www.googleapis.com/auth/gmail.readonly`: Read-only access to email metadata and content

**Note**: If you modify the scopes in the code, delete `token.json` to trigger re-authorization.

## Troubleshooting

### "Error fetching emails"
- Verify `credentials.json` is present and valid
- Check that Gmail API is enabled in Google Cloud Console
- Delete `token.json` and re-authenticate

### "Email body not loading"
- Check console for error messages
- Verify the email exists in your Gmail account
- Some emails may have empty bodies (forwards, calendar invites, etc.)

### "Wrong timezone displayed"
- The app uses `datetime.fromtimestamp()` to convert to local time
- Verify your system timezone is set correctly

### Server won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Ensure `.env` file exists with valid `ANTHROPIC_API_KEY`

## Development Status

This tool is in active development. Current version: **v0.1**

Planned enhancements:
- Support for multiple email accounts
- Email filtering and search
- Prompt templates library
- Export conversation history
- Multi-model support (OpenAI, Gemini, etc.)

## Related Projects

This tool was developed alongside [Multi_Agent_Email_tool](https://github.com/yourusername/Multi_Agent_Email_tool), a production email automation system. Shared Gmail functions may eventually be extracted into a separate `gmail-utils` library.

## License

MIT License

## Security Notes

- Never commit `credentials.json`, `token.json`, or `.env` files
- Keep your API keys secure
- Review OAuth permissions before authorizing
- This tool has read-only Gmail access

## Acknowledgments

- Built with [Claude](https://claude.ai) - Anthropic's AI assistant
- Uses Gmail API for email access
- Markdown rendering by [marked.js](https://marked.js.org/)
- HTML sanitization by [DOMPurify](https://github.com/cure53/DOMPurify)
