from typing import Optional
from app.services.event_store import EventStore
from app.services.command_handler import CommandHandler
from app.services.query_handler import QueryHandler

_event_store: Optional[EventStore] = None
_command_handler: Optional[CommandHandler] = None
_query_handler: Optional[QueryHandler] = None

def get_event_store() -> EventStore:
    """Get singleton EventStore instance."""
    global _event_store
    if _event_store is None:
        _event_store = EventStore()
    return _event_store

def get_command_handler() -> CommandHandler:
    """Get singleton CommandHandler instance."""
    global _command_handler
    if _command_handler is None:
        _command_handler = CommandHandler(get_event_store())
    return _command_handler

def get_query_handler() -> QueryHandler:
    """Get singleton QueryHandler instance."""
    global _query_handler
    if _query_handler is None:
        _query_handler = QueryHandler(get_event_store())
    return _query_handler

