import base64
import copy
import logging
import uuid
from datetime import datetime,timezone

from typing import Any, Optional, Dict, List, Set

import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ConfigurationError, PyMongoError, DuplicateKeyError
from pymongo.client_session import ClientSession
from typing_extensions import override

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import BaseSessionService, GetSessionConfig, ListEventsResponse, ListSessionsResponse
from google.adk.sessions.session import Session
from google.adk.sessions.state import State


logger = logging.getLogger(__name__)

# Collection Names
SESSIONS_COLLECTION = "sessions"
EVENTS_COLLECTION = "events"
APP_STATES_COLLECTION = "app_states"
USER_STATES_COLLECTION = "user_states"

class MongoDBSessionService(BaseSessionService):
    """A session service that uses MongoDB for storage."""

    def __init__(self, db_url: str, db_name: str = "taxagent_session_service"):
        """Initializes the MongoDB session service.

        Args:
            db_url: MongoDB connection string.
            db_name: Name of the database to use.

        Raises:
            ValueError: If connection to MongoDB fails.
        """
        print(f"MongoDB connection string: {db_url}")  # Debugging line to check the connection string
        try:
            self._client: MongoClient = MongoClient(db_url)
            self._client.admin.command('ping')

        except (ConnectionFailure, ConfigurationError, PyMongoError) as e:
            raise ValueError(f"Failed to connect to MongoDB or configuration error: {str(e)}") from e

        self._db: Database = self._client[db_name]
        self._sessions_collection: Collection = self._db[SESSIONS_COLLECTION]
        self._events_collection: Collection = self._db[EVENTS_COLLECTION]
        self._app_states_collection: Collection = self._db[APP_STATES_COLLECTION]
        self._user_states_collection: Collection = self._db[USER_STATES_COLLECTION]

        self._sessions_collection.create_index([
            ("_id", ASCENDING),
            ("app_name", ASCENDING),
            ("user_id", ASCENDING)
        ]) 

        self._sessions_collection.create_index([
            ("app_name", ASCENDING),
            ("user_id", ASCENDING)
        ])


        self._events_collection.create_index([
            ("session_id", ASCENDING),
            ("timestamp", ASCENDING)
        ])
        self._events_collection.create_index([
             ("_id", ASCENDING),
             ("app_name", ASCENDING),
             ("user_id", ASCENDING),
             ("session_id", ASCENDING)
        ]) 

        # Index for app states by _id (app_name)
        self._app_states_collection.create_index([("_id", ASCENDING)]) 

        # Index for user states by _id ({app_name, user_id})
        self._user_states_collection.create_index([("_id", ASCENDING)])



    def _extract_state_delta(self, state: Optional[Dict[str, Any]]) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Extracts app, user, and session state deltas from a combined state dictionary."""
        app_state_delta = {}
        user_state_delta = {}
        session_state_delta = {}
        if state:
            for key, value in state.items():
                if key.startswith(State.APP_PREFIX):
                    app_state_delta[key.removeprefix(State.APP_PREFIX)] = value
                elif key.startswith(State.USER_PREFIX):
                    user_state_delta[key.removeprefix(State.USER_PREFIX)] = value
                elif not key.startswith(State.TEMP_PREFIX):
                    session_state_delta[key] = value
        return app_state_delta, user_state_delta, session_state_delta

    def _merge_state(self, app_state: Dict[str, Any], user_state: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Merges app, user, and session states into a single dictionary."""
        # Deep copy session_state to avoid modifying the original dict fetched from DB
        merged_state = copy.deepcopy(session_state)
        for key, value in app_state.items():
            merged_state[State.APP_PREFIX + key] = value
        for key, value in user_state.items():
            merged_state[State.USER_PREFIX + key] = value
        return merged_state

    def _encode_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Encodes event content for storage, handling binary data."""
        if not content:
            return content
        # Deep copy to avoid modifying the original event object's content dict
        encoded_content = copy.deepcopy(content)
        if "parts" in encoded_content:
            for p in encoded_content["parts"]:
                if "inline_data" in p and "data" in p["inline_data"]:
                    # Replicate the original's tuple format for binary data
                    # Ensure data is bytes before encoding
                    data_bytes = p["inline_data"]["data"]
                    if isinstance(data_bytes, str): # If already decoded string, re-encode to bytes
                         data_bytes = data_bytes.encode('utf-8') # Assuming utf-8 if string
                    p["inline_data"]["data"] = (
                        base64.b64encode(data_bytes).decode("utf-8"),
                    )
        return encoded_content

    def _decode_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Decodes stored event content, handling binary data."""
        if not content:
            return content
        decoded_content = copy.deepcopy(content)
        if "parts" in decoded_content:
            for p in decoded_content["parts"]:
                if "inline_data" in p and "data" in p["inline_data"] and isinstance(p["inline_data"]["data"], tuple):
                    # Expecting the tuple format from _encode_content
                    try:
                        p["inline_data"]["data"] = base64.b64decode(p["inline_data"]["data"][0])
                    except (TypeError, IndexError, base64.binascii.Error) as e:
                         logger.warning(f"Failed to base64 decode inline_data: {e}")
                         # Depending on requirements, might raise error or leave as is
                         pass # Leave potentially malformed data in place
        return decoded_content

    def _session_doc_to_obj(self, session_doc: Dict[str, Any], merged_state: Dict[str, Any], events: Optional[List[Event]] = None) -> Session:
         """Converts a MongoDB session document to a Session object."""
         session = Session(
             app_name=session_doc["app_name"],
             user_id=session_doc["user_id"],
             id=session_doc["_id"], # Use _id as session ID
             state=merged_state,
             last_update_time=session_doc["update_time"].timestamp(),
         )
         if events is not None:
             session.events = events
         return session

    def _event_doc_to_obj(self, event_doc: Dict[str, Any]) -> Event:
        """Converts a MongoDB event document to an Event object."""
        actions_data = event_doc.get("actions")
        actions_value_for_event_constructor = actions_data

    
        return Event(
            id=event_doc["_id"], # Use _id as event ID
            author=event_doc["author"],
            branch=event_doc.get("branch"),
            invocation_id=event_doc["invocation_id"],
            content=self._decode_content(event_doc.get("content")) if event_doc.get("content") is not None else None,
            actions=actions_value_for_event_constructor,
            timestamp=event_doc["timestamp"].timestamp(),
            long_running_tool_ids=set(event_doc.get("long_running_tool_ids", [])),
            grounding_metadata=event_doc.get("grounding_metadata"),
            partial=event_doc.get("partial"),
            turn_complete=event_doc.get("turn_complete"),
            error_code=event_doc.get("error_code"),
            error_message=event_doc.get("error_message"),
            interrupted=event_doc.get("interrupted"),
        )


    @override
    def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        session_id = session_id if session_id else str(uuid.uuid4())
        current_time = datetime.now(timezone.utc)

        app_state_delta, user_state_delta, session_state = self._extract_state_delta(state)

        # Start a transaction for atomicity
        with self._client.start_session() as mongo_session:
            mongo_session.start_transaction()
            try:
                # Fetch existing states or prepare for upsert
                app_state_doc = self._app_states_collection.find_one({"_id": app_name}, session=mongo_session)
                user_state_doc = self._user_states_collection.find_one({"_id": {"app_name": app_name, "user_id": user_id}}, session=mongo_session)

                app_state = app_state_doc["state"] if app_state_doc else {}
                user_state = user_state_doc["state"] if user_state_doc else {}

                # Apply state deltas
                app_state.update(app_state_delta)
                user_state.update(user_state_delta)

                # Upsert app state (creates or updates)
                self._app_states_collection.update_one(
                   {"_id": app_name},
                   {"$set": {"state": app_state, "update_time": current_time}},
                   upsert=True,
                   session=mongo_session
               )

                # Upsert user state (creates or updates)
                self._user_states_collection.update_one(
                   {"_id": {"app_name": app_name, "user_id": user_id}},
                   {"$set": {"state": user_state, "update_time": current_time}},
                   upsert=True,
                   session=mongo_session
               )

                # Create session document using session_id as _id
                session_doc = {
                    "_id": session_id, # MongoDB primary key
                    "app_name": app_name,
                    "user_id": user_id,
                    "state": session_state,
                    "create_time": current_time,
                    "update_time": current_time,
                }

                self._sessions_collection.insert_one(session_doc, session=mongo_session)

                mongo_session.commit_transaction()

                # Merge states for response (using the state applied within the transaction)
                merged_state = self._merge_state(app_state, user_state, session_state)

                # Return the Session object using the data just committed
                return self._session_doc_to_obj(session_doc, merged_state)

            except DuplicateKeyError as e:
                 mongo_session.abort_transaction()
                 # Specific error for session ID collision
                 raise ValueError(f"Session with id '{session_id}' already exists for user {user_id} in app {app_name}.") from e
            except Exception as e:
                mongo_session.abort_transaction()
                logger.error(f"Transaction aborted during create_session for {app_name}/{user_id}/{session_id}: {e}")
                raise

    @override
    def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        # Reads generally don't require transactions unless strong snapshot
        # consistency across multiple documents is needed. Sequential reads here.

        session_doc = self._sessions_collection.find_one(
            {"_id": session_id, "app_name": app_name, "user_id": user_id}
        )

        if not session_doc:
            return None

        # Fetch states
        app_state_doc = self._app_states_collection.find_one({"_id": app_name})
        user_state_doc = self._user_states_collection.find_one({"_id": {"app_name": app_name, "user_id": user_id}})

        app_state = app_state_doc["state"] if app_state_doc else {}
        user_state = user_state_doc["state"] if user_state_doc else {}
        session_state = session_doc.get("state", {})

        # Merge states
        merged_state = self._merge_state(app_state, user_state, session_state)

        # Fetch events
        event_query = {"session_id": session_id, "app_name": app_name, "user_id": user_id}
        event_sort = [("timestamp", ASCENDING)] # Default to ascending chronological order
        event_limit = None

        if config:
            if config.after_timestamp is not None:
                 # Convert timestamp float to datetime
                 after_dt = datetime.fromtimestamp(config.after_timestamp)
                 event_query["timestamp"] = {"$lt": after_dt}

            if config.num_recent_events is not None and config.num_recent_events > 0:
                event_limit = config.num_recent_events
                event_sort = [("timestamp", DESCENDING)]


        cursor = self._events_collection.find(event_query).sort(event_sort)
        if event_limit is not None:
             cursor = cursor.limit(event_limit)

        # Convert MongoDB event docs to Event objects
        event_docs = list(cursor)

        # If sorted descending for limit, reverse to restore chronological order
        if event_limit is not None and event_sort[0][1] == DESCENDING:
             event_docs.reverse()

        events: List[Event] = [self._event_doc_to_obj(doc) for doc in event_docs]

        # Return the Session object
        return self._session_doc_to_obj(session_doc, merged_state, events)

    @override
    def list_sessions(
        self, *, app_name: str, user_id: str
    ) -> ListSessionsResponse:
        query = {"app_name": app_name, "user_id": user_id}
        # Project to get only necessary fields efficiently
        projection = {"_id": 1, "update_time": 1, "app_name": 1, "user_id": 1} # Include keys for Session obj construction

        cursor = self._sessions_collection.find(query, projection)

        sessions = []
        for session_doc in cursor:
            # Construct Session objects with minimal info (empty state as per original)
            sessions.append(Session(
                app_name=session_doc["app_name"],
                user_id=session_doc["user_id"],
                id=session_doc["_id"], # Use _id
                state={},
                last_update_time=session_doc["update_time"].timestamp(),
            ))

        return ListSessionsResponse(sessions=sessions)

    @override
    def delete_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> None:
        # Start a transaction for atomicity
        with self._client.start_session() as mongo_session:
            mongo_session.start_transaction()
            try:
                # Delete the session document by _id
                session_result = self._sessions_collection.delete_one(
                    {"_id": session_id, "app_name": app_name, "user_id": user_id},
                    session=mongo_session
                )

                # Delete associated events by session_id
                event_result = self._events_collection.delete_many(
                    {"session_id": session_id, "app_name": app_name, "user_id": user_id},
                    session=mongo_session
                )

                mongo_session.commit_transaction()

                if session_result.deleted_count == 0:
                     logger.warning(f"Attempted to delete session {session_id} for {app_name}/{user_id}, but session was not found.")

            except Exception as e:
                mongo_session.abort_transaction()
                logger.error(f"Transaction aborted during delete_session for {app_name}/{user_id}/{session_id}: {e}")
                raise


    @override
    def append_event(self, session: Session, event: Event) -> Event:
        logger.debug(f"Attempting to append event {event.id} to session {session.id}")
        if event.content is None:
            logger.warning(f"Custom append_event: Event content was None, set to empty string for event {event}")
            return event 
        if event.partial:
            logger.debug(f"Skipping storage for partial event {event.id}")
            return event

        current_time = datetime.now(timezone.utc)

        # Start a transaction for atomicity of state updates and event insertion
        with self._client.start_session() as mongo_session:
            mongo_session.start_transaction()
            try:
                session_doc = self._sessions_collection.find_one(
                    {"_id": session.id, "app_name": session.app_name, "user_id": session.user_id},
                    session=mongo_session
                )

                if not session_doc:
                    raise ValueError(f"Session {session.id} not found for appending event.")

                db_update_timestamp = session_doc["update_time"].replace(tzinfo=timezone.utc).timestamp()
                if db_update_timestamp > session.last_update_time:
                    raise ValueError(
                        f"Session last_update_time {session.last_update_time} is stale."
                        f" Current storage update_time: {db_update_timestamp}"
                    )


                app_state_doc = self._app_states_collection.find_one({"_id": session.app_name}, session=mongo_session)
                user_state_doc = self._user_states_collection.find_one({"_id": {"app_name": session.app_name, "user_id": session.user_id}}, session=mongo_session)
                app_state = app_state_doc["state"] if app_state_doc else {}
                user_state = user_state_doc["state"] if user_state_doc else {}
                session_state = session_doc.get("state", {})
                app_state_delta, user_state_delta, session_state_delta = ({},{},{}) # Default empty


                if event.actions and hasattr(event.actions, 'state_delta') and event.actions.state_delta:
                     app_state_delta, user_state_delta, session_state_delta = (
                         self._extract_state_delta(event.actions.state_delta)
                     )
                     app_state.update(app_state_delta)
                     user_state.update(user_state_delta)
                     session_state.update(session_state_delta)


                # 1. Update App State (using upsert=True for robustness, though should exist)
                if app_state_delta: # Only update if there's a delta
                     self._app_states_collection.update_one(
                        {"_id": session.app_name},
                        {"$set": {"state": app_state, "update_time": current_time}},
                        upsert=True,
                        session=mongo_session
                     )

                # 2. Update User State (using upsert=True for robustness)
                if user_state_delta: # Only update if there's a delta
                     self._user_states_collection.update_one(
                        {"_id": {"app_name": session.app_name, "user_id": session.user_id}},
                        {"$set": {"state": user_state, "update_time": current_time}},
                        upsert=True,
                        session=mongo_session
                     )

                # 3. Update Session State and update_time
                # Update session doc if there were session state changes or just to bump update_time
                if session_state_delta or app_state_delta or user_state_delta:
                     self._sessions_collection.update_one(
                        {"_id": session.id},
                        {"$set": {"state": session_state, "update_time": current_time}},
                        session=mongo_session
                     )


                # 4. Insert Event document using event.id as _id
                event_doc = {
                    "_id": event.id, # MongoDB primary key
                    "invocation_id": event.invocation_id,
                    "author": event.author,
                    "branch": event.branch,
                    "actions": event.actions.model_dump(exclude_none=True) if event.actions else None,
                    "session_id": session.id,
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                    "timestamp": datetime.fromtimestamp(event.timestamp),
                    "long_running_tool_ids": list(event.long_running_tool_ids) if event.long_running_tool_ids else [],
                    "grounding_metadata": event.grounding_metadata,
                    "partial": event.partial,
                    "turn_complete": event.turn_complete,
                    "error_code": event.error_code,
                    "error_message": event.error_message,
                    "interrupted": event.interrupted,
                    # Encode content before storing
                    "content": self._encode_content(event.content.model_dump(exclude_none=True) if event.content else {})
                }

                self._events_collection.insert_one(event_doc, session=mongo_session)

                mongo_session.commit_transaction()
                logger.debug(f"Transaction committed for append_event {event.id}")

                session.last_update_time = current_time.timestamp()


                super().append_event(session=session, event=event)
                return event

            except Exception as e:
                mongo_session.abort_transaction()
                logger.error(f"Transaction aborted during append_event for session {session.id}, event {event.id}: {e}")
                raise


    @override
    def list_events(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> ListEventsResponse:
        event_query = {
             "app_name": app_name,
             "user_id": user_id,
             "session_id": session_id
        }
        events_cursor = self._events_collection.find(event_query).sort("timestamp", ASCENDING)

        # Convert MongoDB event docs to Event objects
        events: List[Event] = [self._event_doc_to_obj(doc) for doc in events_cursor]

        return ListEventsResponse(events=events)

    def close(self):
        """Closes the MongoDB connection."""
        if hasattr(self, "_client") and self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")

    def __del__(self):
         # Ensure connection is closed when object is garbage collected
         try:
              self.close()
         except Exception:
              pass # Ignore errors during garbage collection