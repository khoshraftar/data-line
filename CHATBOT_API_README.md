# Khodroyar Chatbot API Documentation

## Overview

The Khodroyar chatbot API handles the new message format by using existing conversation IDs to identify users and process messages.

## API Endpoints

### Receive Message Endpoint

**URL:** `POST /khodroyar/api/chat/receive/`

**Description:** Receives and processes chatbot messages from users.

#### Message Format

The API supports the following message structure:

```json
{
    "type": "NEW_CHATBOT_MESSAGE",
    "new_chatbot_message": {
        "id": "7651e778-6231-11f0-a7fd-5607f0c4facf",
        "conversation": {
            "id": "1fad7e32-b2ea-4084-8ec9-e6265136e963",
            "type": "BOT"
        },
        "sender": {
            "type": "HUMAN"
        },
        "type": "TEXT",
        "sent_at": "2025-07-16T10:41:42.648410Z",
        "text": "test_message"
    }
}
```

**Response (Success):**
```json
{
    "success": true,
    "data": {
        "conversation_id": "1fad7e32-b2ea-4084-8ec9-e6265136e963",
        "bot_response": "سلام! من ربات خودرویار هستم...",
        "message_id": 123,
        "user_message_id": 122
    }
}
```

**Response (Conversation Not Found):**
```json
{
    "success": false,
    "error": "Conversation with ID 1fad7e32-b2ea-4084-8ec9-e6265136e963 not found"
}
```

**Response (Missing Required Fields):**
```json
{
    "success": false,
    "error": "Message text is required"
}
```

## Implementation Details

### Message Processing Flow

1. **Message Reception**: The API receives messages in the new format
2. **Validation**: Validates that required fields (text, conversation_id) are present
3. **Conversation Lookup**: Retrieves the existing conversation using the conversation_id
4. **User Identification**: Gets the user from the conversation
5. **Message Storage**: Saves user messages with rich metadata
6. **Response Generation**: Processes the message and generates bot responses
7. **Response Storage**: Saves bot responses to the database

### Assumptions

- **Conversation Exists**: The API assumes that the conversation with the provided `conversation_id` already exists in the database
- **User Authentication**: User authentication is handled through the existing conversation
- **Required Fields**: Both `text` and `conversation.id` are required fields

### Metadata Storage

The implementation stores rich metadata for each message:

- `message_id`: Original message ID from the sender
- `sent_at`: Original timestamp from the sender
- `message_type`: Type of message (TEXT, etc.)
- `sender_type`: Type of sender (HUMAN, BOT)
- `conversation_type`: Type of conversation (BOT, etc.)
- `timestamp`: Local timestamp when message was processed

## Testing

Use the provided test script to test the API:

```bash
python test_chatbot_api.py
```

Make sure to:
1. Start your Django server
2. Update the `BASE_URL` in the test script if needed
3. Ensure you have test conversations in your database

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid JSON or missing required fields (text, conversation_id)
- **404 Not Found**: Conversation with the provided ID doesn't exist
- **500 Internal Server Error**: Unexpected server errors

## Database Schema

The implementation uses the following models:

- **UserAuth**: Stores user authentication information
- **Conversation**: Stores conversation metadata (must exist before API calls)
- **Message**: Stores individual messages with rich metadata

## Security Considerations

- CSRF protection is disabled for API endpoints using `@csrf_exempt`
- User authentication is handled through existing conversations
- All API endpoints validate input data
- Error messages don't expose sensitive information

## Usage Example

```python
import requests
import json

# Sample message
message = {
    "type": "NEW_CHATBOT_MESSAGE",
    "new_chatbot_message": {
        "id": "7651e778-6231-11f0-a7fd-5607f0c4facf",
        "conversation": {
            "id": "1fad7e32-b2ea-4084-8ec9-e6265136e963",
            "type": "BOT"
        },
        "sender": {
            "type": "HUMAN"
        },
        "type": "TEXT",
        "sent_at": "2025-07-16T10:41:42.648410Z",
        "text": "سلام"
    }
}

# Send to API
response = requests.post(
    "http://localhost:8000/khodroyar/api/chat/receive/",
    json=message
)

print(response.json())
```

## Prerequisites

Before using the API, ensure that:

1. The conversation with the specified `conversation_id` exists in the database
2. The conversation is associated with a valid user authentication record
3. The Django server is running and accessible 