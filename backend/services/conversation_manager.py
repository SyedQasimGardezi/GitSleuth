import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from models.schemas import ConversationMessage, ConversationHistory

class ConversationManager:
    def __init__(self):
        # In-memory storage for conversations (in production, use Redis or database)
        self.conversations: Dict[str, ConversationHistory] = {}
    
    def create_conversation(self, session_id: str) -> str:
        """Create a new conversation for a session"""
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        
        conversation = ConversationHistory(
            session_id=session_id,
            messages=[],
            created_at=now,
            updated_at=now
        )
        
        self.conversations[conversation_id] = conversation
        return conversation_id
    
    def add_message(self, conversation_id: str, role: str, content: str, confidence: Optional[str] = None) -> bool:
        """Add a message to the conversation"""
        if conversation_id not in self.conversations:
            return False
        
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            confidence=confidence
        )
        
        self.conversations[conversation_id].messages.append(message)
        self.conversations[conversation_id].updated_at = datetime.now()
        return True
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationHistory]:
        """Get conversation by ID"""
        return self.conversations.get(conversation_id)
    
    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history for context"""
        if conversation_id not in self.conversations:
            return []
        
        messages = self.conversations[conversation_id].messages
        recent_messages = messages[-limit:] if len(messages) > limit else messages
        
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
        """Get conversation context for LLM prompt"""
        if conversation_id not in self.conversations:
            return ""
        
        messages = self.conversations[conversation_id].messages
        context_parts = []
        current_tokens = 0
        
        # Start from most recent messages and work backwards
        for msg in reversed(messages):
            msg_text = f"{msg.role}: {msg.content}"
            msg_tokens = len(msg_text.split())  # Rough token estimation
            
            if current_tokens + msg_tokens > max_tokens:
                break
            
            context_parts.insert(0, msg_text)
            current_tokens += msg_tokens
        
        return "\n".join(context_parts)
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear all messages from a conversation"""
        if conversation_id not in self.conversations:
            return False
        
        self.conversations[conversation_id].messages = []
        self.conversations[conversation_id].updated_at = datetime.now()
        return True
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation entirely"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation statistics"""
        if conversation_id not in self.conversations:
            return {}
        
        conversation = self.conversations[conversation_id]
        messages = conversation.messages
        
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "conversation_id": conversation_id
        }
