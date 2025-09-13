import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from models.schemas import ConversationMessage, ConversationHistory
from collections import deque
import threading
import re

try:
    import tiktoken
    tokenizer = tiktoken.get_encoding("cl100k_base")
except ImportError:
    tokenizer = None


class ConversationManager:
    def __init__(self, max_messages: int = 1000):
        """
        In-memory conversation manager.
        In production, replace with Redis or DB backend.
        """
        self.conversations: Dict[str, ConversationHistory] = {}
        self.max_messages = max_messages
        self.lock = threading.Lock()  # Thread-safety for async/background tasks

    def create_conversation(self, session_id: str) -> str:
        """Create a new conversation for a session"""
        conversation_id = str(uuid.uuid4())
        now = datetime.now()

        conversation = ConversationHistory(
            session_id=session_id,
            messages=deque(maxlen=self.max_messages),
            created_at=now,
            updated_at=now
        )

        with self.lock:
            self.conversations[conversation_id] = conversation

        return conversation_id

    def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str, 
        confidence: Optional[str] = None
    ) -> bool:
        """Add a message to the conversation, storing confidence if provided."""
        with self.lock:
            conversation = self.conversations.get(conversation_id)
            if not conversation:
                return False

            # Ensure confidence is one of 'high', 'medium', 'low', or None
            if confidence not in ("high", "medium", "low"):
                # Auto-detect confidence for assistant messages if missing
                if role == "assistant":
                    confidence = self.estimate_confidence(content)
                else:
                    confidence = None

            message = ConversationMessage(
                role=role,
                content=content.strip(),
                timestamp=datetime.now(),
                confidence=confidence
            )

            conversation.messages.append(message)
            conversation.updated_at = datetime.now()

        return True

    def estimate_confidence(self, answer: str) -> str:
        """Heuristic to determine confidence based on answer text."""
        answer_lower = answer.lower()
        # LLM might explicitly include [CONFIDENCE: high/medium/low]
        match = re.search(r"\[CONFIDENCE:\s*(high|medium|low)\]", answer_lower)
        if match:
            return match.group(1)

        # Heuristic based on keywords
        if any(kw in answer_lower for kw in ["i am confident", "definitely", "certainly", "without doubt"]):
            return "high"
        elif any(kw in answer_lower for kw in ["probably", "likely", "may", "might"]):
            return "medium"
        else:
            return "low"

    def get_conversation(self, conversation_id: str) -> Optional[ConversationHistory]:
        """Get conversation by ID"""
        return self.conversations.get(conversation_id)

    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history for context (includes confidence)"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []

        recent_messages = list(conversation.messages)[-limit:]
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "confidence": msg.confidence
            }
            for msg in recent_messages
        ]

    def get_conversation_context(self, conversation_id: str, max_tokens: int = 2000) -> str:
        """Get conversation context for LLM prompt (token-aware if possible)"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return ""

        messages = list(conversation.messages)
        context_parts = []
        current_tokens = 0

        for msg in reversed(messages):
            msg_text = f"{msg.role}: {msg.content}"
            msg_tokens = len(tokenizer.encode(msg_text)) if tokenizer else len(msg_text.split())
            if current_tokens + msg_tokens > max_tokens:
                break
            context_parts.insert(0, msg_text)
            current_tokens += msg_tokens

        return "\n".join(context_parts)

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear all messages from a conversation"""
        with self.lock:
            conversation = self.conversations.get(conversation_id)
            if not conversation:
                return False
            conversation.messages.clear()
            conversation.updated_at = datetime.now()
        return True

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation entirely"""
        with self.lock:
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
                return True
        return False

    def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation statistics"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return {}

        messages = list(conversation.messages)
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]

        return {
            "conversation_id": conversation_id,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "avg_message_length": (
                sum(len(m.content) for m in messages) / len(messages) if messages else 0
            ),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "duration_seconds": (conversation.updated_at - conversation.created_at).total_seconds()
        }
