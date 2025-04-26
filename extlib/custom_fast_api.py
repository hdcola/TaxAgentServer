import asyncio
from contextlib import asynccontextmanager
import importlib
import inspect
import json
import logging
import os
from pathlib import Path
import re
import sys
import traceback
import graphviz
from typing import (
    Any, List, Literal, Optional)
import click
from click import Tuple
from fastapi import (
    FastAPI, HTTPException, Query, Depends, status)
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import export, TracerProvider
from pydantic import ValidationError
from starlette.types import Lifespan

from google.genai import types
from google.adk.agents import RunConfig
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.agents.llm_agent import Agent
from google.adk.agents.run_config import StreamingMode
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner

from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.cli.cli_eval import EVAL_SESSION_ID_PREFIX
from google.adk.cli.utils import create_empty_state, envs, evals
from google.adk.cli.fast_api import ApiServerSpanExporter, AgentRunRequest, AddSessionToEvalSetRequest, RunEvalRequest, RunEvalResult, _EVAL_SET_FILE_EXTENSION

# import custom session service
from .custom_sessions import MyDatabaseSessionService
# import auth dependencies
from .auth.auth_dependencies import get_current_active_user # For HTTP routes
from .auth.jwt_handler import verify_internal_token, credentials_exception, expired_token_exception # For WebSocket manual check
from .auth.database import User as DBUser # Import your SQLAlchemy User model
from .auth.auth_models import TokenPayload # To type hint token payload


logger = logging.getLogger(__name__)

def get_my_fast_api_app(
    *,
    agent_dir: str,
    session_db_url: str = "",
    allow_origins: Optional[list[str]] = None,
    web: bool,
    trace_to_cloud: bool = False,
    lifespan: Optional[Lifespan[FastAPI]] = None,
) -> FastAPI:
    trace_dict: dict[str, Any] = {}

    provider = TracerProvider()
    provider.add_span_processor(
        export.SimpleSpanProcessor(ApiServerSpanExporter(trace_dict))
    )
    if trace_to_cloud:
        envs.load_dotenv_for_agent("", agent_dir)
        if project_id := os.environ.get("GOOGLE_CLOUD_PROJECT", None):
            processor = export.BatchSpanProcessor(
                CloudTraceSpanExporter(project_id=project_id)
            )
            provider.add_span_processor(processor)
        else:
            logging.warning(
                "GOOGLE_CLOUD_PROJECT environment variable is not set. Tracing will"
                " not be enabled."
            )
    trace.set_tracer_provider(provider)

    exit_stacks = []
    @asynccontextmanager
    async def internal_lifespan(app: FastAPI):
        if lifespan:
            async with lifespan(app) as lifespan_context:
                yield

                if exit_stacks:
                    for stack in exit_stacks:
                        await stack.aclose()
        else:
            yield

    app = FastAPI(lifespan=internal_lifespan)

    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if agent_dir not in sys.path:
        sys.path.append(agent_dir)

    runner_dict = {}
    root_agent_dict = {}

    # Build the Artifact service
    artifact_service = InMemoryArtifactService()
    memory_service = InMemoryMemoryService()

  # Build the Session service
    agent_engine_id = ""
    if session_db_url:
        if session_db_url.startswith("agentengine://"):
            # Create vertex session service
            agent_engine_id = session_db_url.split("://")[1]
            if not agent_engine_id:
                raise click.ClickException("Agent engine id can not be empty.")
            envs.load_dotenv_for_agent("", agent_dir)
            session_service = VertexAiSessionService(
                os.environ["GOOGLE_CLOUD_PROJECT"],
                os.environ["GOOGLE_CLOUD_LOCATION"],
            )
        else:
            session_service = MyDatabaseSessionService(db_url=session_db_url)
    else:
        session_service = InMemorySessionService()

    @app.get("/list-apps")
    def list_apps() -> list[str]:
        base_path = Path.cwd() / agent_dir
        if not base_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        if not base_path.is_dir():
            raise HTTPException(status_code=400, detail="Not a directory")
        agent_names = [
            x
            for x in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, x))
            and not x.startswith(".")
            and x != "__pycache__"
        ]
        agent_names.sort()
        return agent_names

    @app.get("/debug/trace/{event_id}")
    def get_trace_dict(event_id: str) -> Any:
        event_dict = trace_dict.get(event_id, None)
        if event_dict is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return event_dict

    @app.get(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}",
        response_model_exclude_none=True,
    )
    def get_session(app_name: str, user_id: str, session_id: str, 
                    current_user: DBUser = Depends(get_current_active_user) # Add dependency
                    ) -> Session:
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's session")
 
        app_name = agent_engine_id if agent_engine_id else app_name
        session = session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    @app.get(
        "/apps/{app_name}/users/{user_id}/sessions",
        response_model_exclude_none=True,
    )
    def list_sessions(app_name: str, user_id: str,
                    current_user: DBUser = Depends(get_current_active_user) # Add dependency 
                      ) -> list[Session]:
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's sessions")
        # Connect to managed session if agent_engine_id is set.
        app_name = agent_engine_id if agent_engine_id else app_name
        return [
            session
            for session in session_service.list_sessions(
                app_name=app_name, user_id=user_id
            ).sessions
            # Remove sessions that were generated as a part of Eval.
            if not session.id.startswith(EVAL_SESSION_ID_PREFIX)
        ]

    @app.post(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}",
        response_model_exclude_none=True,
    )
    def create_session_with_id(
            app_name: str,
            user_id: str,
            session_id: str,
            state: Optional[dict[str, Any]] = None,
            current_user: DBUser = Depends(get_current_active_user) # Add dependency
    ) -> Session:
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's session")
        # Connect to managed session if agent_engine_id is set.
        app_name = agent_engine_id if agent_engine_id else app_name
        if (
                session_service.get_session(
                    app_name=app_name, user_id=user_id, session_id=session_id
                )
                is not None
        ):
            logger.warning("Session already exists: %s", session_id)
            raise HTTPException(
                status_code=400, detail=f"Session already exists: {session_id}"
            )

        logger.info("New session created: %s", session_id)
        return session_service.create_session(
            app_name=app_name, user_id=user_id, state=state, session_id=session_id
        )

    @app.post(
        "/apps/{app_name}/users/{user_id}/sessions",
        response_model_exclude_none=True,
    )
    def create_session(
            app_name: str,
            user_id: str,
            state: Optional[dict[str, Any]] = None,
            current_user: DBUser = Depends(get_current_active_user) # Add dependency
    ) -> Session:
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's session")
        # Connect to managed session if agent_engine_id is set.
        app_name = agent_engine_id if agent_engine_id else app_name

        logger.info("New session created")
        return session_service.create_session(
            app_name=app_name, user_id=user_id, state=state
        )

    def _get_eval_set_file_path(app_name, agent_dir, eval_set_id) -> str:
        return os.path.join(
            agent_dir,
            app_name,
            eval_set_id + _EVAL_SET_FILE_EXTENSION,
            )

    @app.post(
        "/apps/{app_name}/eval_sets/{eval_set_id}",
        response_model_exclude_none=True,
    )
    def create_eval_set(
            app_name: str,
            eval_set_id: str,
    ):
        """Creates an eval set, given the id."""
        pattern = r"^[a-zA-Z0-9_]+$"
        if not bool(re.fullmatch(pattern, eval_set_id)):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid eval set id. Eval set id should have the `{pattern}`"
                    " format"
                ),
            )
        # Define the file path
        new_eval_set_path = _get_eval_set_file_path(
            app_name, agent_dir, eval_set_id
        )

        logger.info("Creating eval set file `%s`", new_eval_set_path)

        if not os.path.exists(new_eval_set_path):
            # Write the JSON string to the file
            logger.info("Eval set file doesn't exist, we will create a new one.")
            with open(new_eval_set_path, "w") as f:
                empty_content = json.dumps([], indent=2)
                f.write(empty_content)

    @app.get(
        "/apps/{app_name}/eval_sets",
        response_model_exclude_none=True,
    )
    def list_eval_sets(app_name: str) -> list[str]:
        """Lists all eval sets for the given app."""
        eval_set_file_path = os.path.join(agent_dir, app_name)
        eval_sets = []
        for file in os.listdir(eval_set_file_path):
            if file.endswith(_EVAL_SET_FILE_EXTENSION):
                eval_sets.append(
                    os.path.basename(file).removesuffix(_EVAL_SET_FILE_EXTENSION)
                )

        return sorted(eval_sets)

    @app.post(
        "/apps/{app_name}/eval_sets/{eval_set_id}/add_session",
        response_model_exclude_none=True,
    )
    async def add_session_to_eval_set(
            app_name: str, eval_set_id: str, req: AddSessionToEvalSetRequest
    ):
        pattern = r"^[a-zA-Z0-9_]+$"
        if not bool(re.fullmatch(pattern, req.eval_id)):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid eval id. Eval id should have the `{pattern}` format",
            )

        # Get the session
        session = session_service.get_session(
            app_name=app_name, user_id=req.user_id, session_id=req.session_id
        )
        assert session, "Session not found."
        # Load the eval set file data
        eval_set_file_path = _get_eval_set_file_path(
            app_name, agent_dir, eval_set_id
        )
        with open(eval_set_file_path, "r") as file:
            eval_set_data = json.load(file)  # Load JSON into a list

        if [x for x in eval_set_data if x["name"] == req.eval_id]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Eval id `{req.eval_id}` already exists in `{eval_set_id}`"
                    " eval set."
                ),
            )

        # Convert the session data to evaluation format
        test_data = evals.convert_session_to_eval_format(session)

        # Populate the session with initial session state.
        initial_session_state = create_empty_state(
            await _get_root_agent_async(app_name)
        )

        eval_set_data.append({
            "name": req.eval_id,
            "data": test_data,
            "initial_session": {
                "state": initial_session_state,
                "app_name": app_name,
                "user_id": req.user_id,
            },
        })
        # Serialize the test data to JSON and write to the eval set file.
        with open(eval_set_file_path, "w") as f:
            f.write(json.dumps(eval_set_data, indent=2))

    @app.get(
        "/apps/{app_name}/eval_sets/{eval_set_id}/evals",
        response_model_exclude_none=True,
    )
    def list_evals_in_eval_set(
            app_name: str,
            eval_set_id: str,
    ) -> list[str]:
        """Lists all evals in an eval set."""
        # Load the eval set file data
        eval_set_file_path = _get_eval_set_file_path(
            app_name, agent_dir, eval_set_id
        )
        with open(eval_set_file_path, "r") as file:
            eval_set_data = json.load(file)  # Load JSON into a list

        return sorted([x["name"] for x in eval_set_data])

    @app.post(
        "/apps/{app_name}/eval_sets/{eval_set_id}/run_eval",
        response_model_exclude_none=True,
    )
    async def run_eval(
            app_name: str, eval_set_id: str, req: RunEvalRequest
    ) -> list[RunEvalResult]:
        from google.adk.cli.cli_eval import run_evals

        """Runs an eval given the details in the eval request."""
        # Create a mapping from eval set file to all the evals that needed to be
        # run.
        eval_set_file_path = _get_eval_set_file_path(
            app_name, agent_dir, eval_set_id
        )
        eval_set_to_evals = {eval_set_file_path: req.eval_ids}

        if not req.eval_ids:
            logger.info(
                "Eval ids to run list is empty. We will all evals in the eval set."
            )
        root_agent = await _get_root_agent_async(app_name)
        eval_results = list(
            run_evals(
                eval_set_to_evals,
                root_agent,
                getattr(root_agent, "reset_data", None),
                req.eval_metrics,
                session_service=session_service,
                artifact_service=artifact_service,
            )
        )

        run_eval_results = []
        for eval_result in eval_results:
            run_eval_results.append(
                RunEvalResult(
                    app_name=app_name,
                    eval_set_id=eval_set_id,
                    eval_id=eval_result.eval_id,
                    final_eval_status=eval_result.final_eval_status,
                    eval_metric_results=eval_result.eval_metric_results,
                    session_id=eval_result.session_id,
                )
            )
        return run_eval_results

    @app.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
    def delete_session(app_name: str, user_id: str, session_id: str,
                          current_user: DBUser = Depends(get_current_active_user) # Add dependency 
        ):
        # Connect to managed session if agent_engine_id is set.
        app_name = agent_engine_id if agent_engine_id else app_name
        session_service.delete_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        logger.info("Session deleted: %s", session_id)
        return {"message": "Session deleted"}
    

    @app.get(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}",
        response_model_exclude_none=True,
    )
    def load_artifact(
            app_name: str,
            user_id: str,
            session_id: str,
            artifact_name: str,
            version: Optional[int] = Query(None),
            current_user: DBUser = Depends(get_current_active_user) # Add dependency
    ) -> Optional[types.Part]:
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's artifact")
        app_name = agent_engine_id if agent_engine_id else app_name
        artifact = artifact_service.load_artifact(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=artifact_name,
            version=version,
        )
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return artifact

    @app.get(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}/versions/{version_id}",
        response_model_exclude_none=True,
    )
    def load_artifact_version(
            app_name: str,
            user_id: str,
            session_id: str,
            artifact_name: str,
            version_id: int,
            current_user: DBUser = Depends(get_current_active_user) # Add dependency
    ) -> Optional[types.Part]:
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's artifact")
        app_name = agent_engine_id if agent_engine_id else app_name
        artifact = artifact_service.load_artifact(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=artifact_name,
            version=version_id,
        )
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return artifact

    @app.get(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts",
        response_model_exclude_none=True,
    )
    def list_artifact_names(
            app_name: str, user_id: str, session_id: str
    ) -> list[str]:
        app_name = agent_engine_id if agent_engine_id else app_name
        return artifact_service.list_artifact_keys(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

    @app.get(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}/versions",
        response_model_exclude_none=True,
    )
    def list_artifact_versions(
            app_name: str, user_id: str, session_id: str, artifact_name: str
    ) -> list[int]:
        app_name = agent_engine_id if agent_engine_id else app_name
        return artifact_service.list_versions(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=artifact_name,
        )

    @app.delete(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}",
    )
    def delete_artifact(
            app_name: str, user_id: str, session_id: str, artifact_name: str
    ):
        app_name = agent_engine_id if agent_engine_id else app_name
        artifact_service.delete_artifact(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=artifact_name,
        )

    @app.post("/run", response_model_exclude_none=True)
    async def agent_run(req: AgentRunRequest) -> list[Event]:
        # Connect to managed session if agent_engine_id is set.
        app_id = agent_engine_id if agent_engine_id else req.app_name
        session = session_service.get_session(
            app_name=app_id, user_id=req.user_id, session_id=req.session_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        runner = await _get_runner_async(req.app_name)
        events = [
            event
            async for event in runner.run_async(
                user_id=req.user_id,
                session_id=req.session_id,
                new_message=req.new_message,
            )
        ]
        logger.info("Generated %s events in agent run: %s", len(events), events)
        return events

    @app.post("/run_sse")
    async def agent_run_sse(req: AgentRunRequest) -> StreamingResponse:
        # Connect to managed session if agent_engine_id is set.
        app_id = agent_engine_id if agent_engine_id else req.app_name
        # SSE endpoint
        session = session_service.get_session(
            app_name=app_id, user_id=req.user_id, session_id=req.session_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Convert the events to properly formatted SSE
        async def event_generator():
            try:
                stream_mode = StreamingMode.SSE if req.streaming else StreamingMode.NONE
                runner = await _get_runner_async(req.app_name)
                async for event in runner.run_async(
                        user_id=req.user_id,
                        session_id=req.session_id,
                        new_message=req.new_message,
                        run_config=RunConfig(streaming_mode=stream_mode),
                ):
                    # Format as SSE data
                    sse_event = event.model_dump_json(exclude_none=True, by_alias=True)
                    logger.info("Generated event in agent run streaming: %s", sse_event)
                    yield f"data: {sse_event}\n\n"
            except Exception as e:
                logger.exception("Error in event_generator: %s", e)
                # You might want to yield an error event here
                yield f'data: {{"error": "{str(e)}"}}\n\n'

        # Returns a streaming response with the proper media type for SSE
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    @app.get(
        "/apps/{app_name}/users/{user_id}/sessions/{session_id}/events/{event_id}/graph",
        response_model_exclude_none=True,
    )
    async def get_event_graph(
            app_name: str, user_id: str, session_id: str, event_id: str,
            current_user: DBUser = Depends(get_current_active_user) # Add dependency
    ):
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's session")
        # Connect to managed session if agent_engine_id is set.
        app_id = agent_engine_id if agent_engine_id else app_name
        session = session_service.get_session(
            app_name=app_id, user_id=user_id, session_id=session_id
        )
        session_events = session.events if session else []
        event = next((x for x in session_events if x.id == event_id), None)
        if not event:
            return {}

        from . import agent_graph

        function_calls = event.get_function_calls()
        function_responses = event.get_function_responses()
        root_agent = await _get_root_agent_async(app_name)
        dot_graph = None
        if function_calls:
            function_call_highlights = []
            for function_call in function_calls:
                from_name = event.author
                to_name = function_call.name
                function_call_highlights.append((from_name, to_name))
                dot_graph = agent_graph.get_agent_graph(
                    root_agent, function_call_highlights
                )
        elif function_responses:
            function_responses_highlights = []
            for function_response in function_responses:
                from_name = function_response.name
                to_name = event.author
                function_responses_highlights.append((from_name, to_name))
                dot_graph = agent_graph.get_agent_graph(
                    root_agent, function_responses_highlights
                )
        else:
            from_name = event.author
            to_name = ""
            dot_graph = agent_graph.get_agent_graph(
                root_agent, [(from_name, to_name)]
            )
        if dot_graph and isinstance(dot_graph, graphviz.Digraph):
            return {"dot_src": dot_graph.source}
        else:
            return {}

    @app.websocket("/run_live")
    async def agent_live_run(
            websocket: WebSocket,
            app_name: str,
            user_id: str,
            session_id: str,
            modalities: List[Literal["TEXT", "AUDIO"]] = Query(
                default=["TEXT", "AUDIO"]
            ),  # Only allows "TEXT" or "AUDIO"
            token: Optional[str] = Query(None), # Make token optional initially

    ) -> None:
        authenticated_user_id: Optional[str] = None # Initialize
        token_payload: Optional[TokenPayload] = None

        # --- WebSocket Authentication Step ---
        if not token:
             print("WS Error: Connection attempt without token.")
             await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
             return

        try:
            # Verify the token provided in the query parameter
            token_payload = verify_internal_token(token)
            authenticated_user_id = token_payload.sub # Get user ID FROM THE TOKEN
            if not authenticated_user_id:
                 # Should be caught by verify_internal_token, but defensive check
                 raise credentials_exception

            print(f"WS Authentication successful for user: {authenticated_user_id}")
            await websocket.accept() # Accept connection ONLY after successful auth

        except HTTPException as auth_exc:
            print(f"WS Auth Error: {auth_exc.detail}")
            reason = f"Authentication failed: {auth_exc.detail}"
            close_code = status.WS_1008_POLICY_VIOLATION # Generic policy violation
            if auth_exc.status_code == status.HTTP_401_UNAUTHORIZED:
                 if "expired" in auth_exc.detail.lower():
                     reason = "Token has expired" # More specific reason
                 else:
                     reason = "Invalid token"
            await websocket.close(code=close_code, reason=reason)
            return # Stop processing if auth fails
        except Exception as e:
            # Catch unexpected errors during verification
            print(f"WS Unexpected Auth Error: {e}")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error during authentication")
            return # Stop processing

        # --- Proceed only if authenticated ---
        if not authenticated_user_id:
             await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Authentication failed unexpectedly")
             return        
        # --- WebSocket Authentication Finished ---
        # Connect to managed session if agent_engine_id is set.
        app_id = agent_engine_id if agent_engine_id else app_name
        session = session_service.get_session(
            app_name=app_id, user_id=user_id, session_id=session_id
        )
        if not session:
            # Accept first so that the client is aware of connection establishment,
            # then close with a specific code.
            await websocket.close(code=1002, reason="Session not found")
            return

        live_request_queue = LiveRequestQueue()

        async def forward_events():
            runner = await _get_runner_async(app_name)
            async for event in runner.run_live(
                    session=session, live_request_queue=live_request_queue
            ):
                await websocket.send_text(
                    event.model_dump_json(exclude_none=True, by_alias=True)
                )

        async def process_messages():
            try:
                while True:
                    data = await websocket.receive_text()
                    # Validate and send the received message to the live queue.
                    live_request_queue.send(LiveRequest.model_validate_json(data))
            except ValidationError as ve:
                logger.error("Validation error in process_messages: %s", ve)

        # Run both tasks concurrently and cancel all if one fails.
        tasks = [
            asyncio.create_task(forward_events()),
            asyncio.create_task(process_messages()),
        ]
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_EXCEPTION
        )
        try:
            # This will re-raise any exception from the completed tasks.
            for task in done:
                task.result()
        except WebSocketDisconnect:
            logger.info("Client disconnected during process_messages.")
        except Exception as e:
            logger.exception("Error during live websocket communication: %s", e)
            traceback.print_exc()
        finally:
            for task in pending:
                task.cancel()

    async def _get_root_agent_async(app_name: str) -> Agent:
        """Returns the root agent for the given app."""
        if app_name in root_agent_dict:
            return root_agent_dict[app_name]
        agent_module = importlib.import_module(app_name)
        if getattr(agent_module.agent, "root_agent"):
            root_agent = agent_module.agent.root_agent
        else:
            raise ValueError(f'Unable to find "root_agent" from {app_name}.')

        # Handle an awaitable root agent and await for the actual agent.
        if inspect.isawaitable(root_agent):
            try:
                agent, exit_stack = await root_agent
                exit_stacks.append(exit_stack)
                root_agent = agent
            except Exception as e:
                raise RuntimeError(f"error getting root agent, {e}") from e

        root_agent_dict[app_name] = root_agent
        return root_agent

    async def _get_runner_async(app_name: str) -> Runner:
        """Returns the runner for the given app."""
        envs.load_dotenv_for_agent(os.path.basename(app_name), agent_dir)
        if app_name in runner_dict:
            return runner_dict[app_name]
        root_agent = await _get_root_agent_async(app_name)
        runner = Runner(
            app_name=agent_engine_id if agent_engine_id else app_name,
            agent=root_agent,
            artifact_service=artifact_service,
            session_service=session_service,
            memory_service=memory_service,
        )
        runner_dict[app_name] = runner
        return runner
    return app