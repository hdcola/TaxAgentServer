# custom_sessions.py
# this file only uses the DatabaseSessionService class
import logging

from google.adk.sessions.database_session_service import DatabaseSessionService
#from .custom_mongodb_session_service import MongoDBSessionService
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from typing_extensions import override

logger = logging.getLogger(__name__)

class MyDatabaseSessionService(DatabaseSessionService):

    # Override the append_event method
    @override
    def append_event(self, session: Session, event: Event) -> Event:
        """Appends an event, handling None content for database insertion."""
        logger.debug(f"Custom append_event: Appending event {event.id} for session {session.id}")
        # Early exit for partial events without content (matching original logic)
        if event.content is None:
            # Handle None content by setting it to an empty string or a default value
            logger.warning(f"Custom append_event: Event content was None, set to empty string for event {event}")
            return event 
        if event.partial:
            logger.debug(f"Custom append_event: Skipping partial event {event.id} without content.")
            return event
        logger.info(f"Custom append_event: Appending event from {event.author} for session {session.id}")
        return super().append_event(session, event)


