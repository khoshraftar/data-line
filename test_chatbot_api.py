#!/usr/bin/env python3
"""
Test script for the new chatbot API format
"""

import json
import requests

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust this to your Django server URL
API_ENDPOINT = f"{BASE_URL}/khodroyar/api/chat/receive/"

def test_new_message_format():
    """Test the new message format"""
    print("Testing new message format...")
    
    # Sample message based on the provided format
    sample_message = {
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
    
    try:
        response = requests.post(API_ENDPOINT, json=sample_message)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_missing_conversation_id():
    """Test with missing conversation ID"""
    print("\nTesting missing conversation ID...")
    
    sample_message = {
        "type": "NEW_CHATBOT_MESSAGE",
        "new_chatbot_message": {
            "id": "7651e778-6231-11f0-a7fd-5607f0c4facf",
            "conversation": {
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
    
    try:
        response = requests.post(API_ENDPOINT, json=sample_message)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_missing_text():
    """Test with missing text"""
    print("\nTesting missing text...")
    
    sample_message = {
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
            "sent_at": "2025-07-16T10:41:42.648410Z"
        }
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=sample_message)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    """Run all tests"""
    print("=== Chatbot API Test Suite ===\n")
    
    # Test new message format
    new_format_result = test_new_message_format()
    
    # Test missing conversation ID
    missing_conv_result = test_missing_conversation_id()
    
    # Test missing text
    missing_text_result = test_missing_text()
    
    print("\n=== Test Summary ===")
    print(f"New Format: {'PASS' if new_format_result and new_format_result.get('success') else 'FAIL'}")
    print(f"Missing Conversation ID: {'PASS' if missing_conv_result and not missing_conv_result.get('success') else 'FAIL'}")
    print(f"Missing Text: {'PASS' if missing_text_result and not missing_text_result.get('success') else 'FAIL'}")

if __name__ == "__main__":
    main() 