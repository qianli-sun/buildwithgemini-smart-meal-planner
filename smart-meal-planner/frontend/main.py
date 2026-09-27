"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import json
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
try:
    from a2a.types import (
        AgentCard,
        FilePart,
        Message,
        Part,
        Role,
        TaskArtifactUpdateEvent,
        TextPart,
        TransportProtocol,
    )
except ImportError:
    from a2a.compat.v0_3.types import (
        AgentCard,
        FilePart,
        Message,
        Part,
        Role,
        TaskArtifactUpdateEvent,
        TextPart,
        TransportProtocol,
    )
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/397009693787/locations/us-east1/reasoningEngines/4770356541431742464",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient):
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        data = resp.json()
        try:
            from a2a.types import AgentCard as ProtoAgentCard
            from google.protobuf.json_format import ParseDict

            card = ProtoAgentCard()
            ParseDict(data, card, ignore_unknown_fields=True)
            if hasattr(card, "url"):
                card.url = A2A_BASE
        except Exception:
            card = AgentCard(**data)
            card.url = A2A_BASE
        _card = card
    return _card


_A2UI_TAG_RE = re.compile(
    r"<a2ui-json>([\s\S]*?)</a2ui-json>|<a2a_datapart_json>([\s\S]*?)</a2a_datapart_json>"
)


def _process_text_for_a2ui(text: str) -> tuple[str, list[dict]]:
    """Extract A2UI JSON payloads embedded inside text, returning cleaned text and a2ui parts."""
    a2ui_parts: list[dict] = []
    matches = list(_A2UI_TAG_RE.finditer(text))
    if not matches:
        return text, []

    for m in matches:
        json_str = (m.group(1) or m.group(2) or "").strip()
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                for item in parsed:
                    a2ui_parts.append({"kind": "a2ui", "data": item})
            elif isinstance(parsed, dict):
                inner = parsed.get("data", parsed)
                if isinstance(inner, list):
                    for item in inner:
                        a2ui_parts.append({"kind": "a2ui", "data": item})
                else:
                    a2ui_parts.append({"kind": "a2ui", "data": inner})
        except Exception:
            pass

    cleaned_text = _A2UI_TAG_RE.sub("", text).strip()
    return cleaned_text, a2ui_parts


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI."""
    out: list[dict] = []
    for p in parts:
        if isinstance(p, dict):
            if "text" in p and p["text"]:
                clean_text, extra_a2ui = _process_text_for_a2ui(p["text"])
                if clean_text:
                    out.append({"kind": "text", "text": clean_text})
                out.extend(extra_a2ui)
            elif "data" in p:
                d = p["data"]
                if isinstance(d, dict):
                    meta = d.get("metadata", {})
                    mime = meta.get("mimeType") if isinstance(meta, dict) else None
                    if mime == _A2UI_MIME:
                        out.append({"kind": "a2ui", "data": d.get("data", d)})
                    elif "data" in d:
                        out.append({"kind": "a2ui", "data": d["data"]})
            elif "file" in p:
                uri = p.get("file", {}).get("uri")
                if uri:
                    out.append({"kind": "text", "text": uri})
            continue

        root = getattr(p, "root", p)
        text_val = getattr(root, "text", None)
        if text_val:
            clean_text, extra_a2ui = _process_text_for_a2ui(text_val)
            if clean_text:
                out.append({"kind": "text", "text": clean_text})
            out.extend(extra_a2ui)
        elif getattr(root, "data", None) is not None:
            data_val = root.data
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": data_val})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        try:
            config = ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        except TypeError:
            config = ClientConfig(httpx_client=client)

        factory = ClientFactory(config)
        a2a_client = factory.create(card)

        context_id = _contexts.get(user_id)
        try:
            from a2a.types import (
                Message as ProtoMessage,
                Part as ProtoPart,
                Role as ProtoRole,
                SendMessageRequest,
            )

            msg = ProtoMessage(
                message_id=str(uuid.uuid4()),
                role=ProtoRole.ROLE_USER,
                parts=[ProtoPart(text=message)],
            )
            if context_id:
                msg.context_id = context_id
            send_payload = SendMessageRequest(message=msg)
        except Exception:
            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(text=message))],
                context_id=context_id,
            )
            send_payload = msg

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(send_payload):
            if hasattr(event, "HasField") or hasattr(event, "DESCRIPTOR"):
                from google.protobuf.json_format import MessageToDict

                d = MessageToDict(event)
                if "task" in d and d["task"].get("contextId"):
                    _contexts[user_id] = d["task"]["contextId"]
                elif "statusUpdate" in d and d["statusUpdate"].get("contextId"):
                    _contexts[user_id] = d["statusUpdate"]["contextId"]
                elif (
                    "artifactUpdate" in d and d["artifactUpdate"].get("contextId")
                ):
                    _contexts[user_id] = d["artifactUpdate"]["contextId"]

                if "artifactUpdate" in d:
                    got_artifact_update = True
                    art = d["artifactUpdate"].get("artifact", {})
                    parts.extend(_extract_parts(art.get("parts", [])))
            elif isinstance(event, tuple):
                task, update = event
                if task is not None:
                    last_task = task
                    if getattr(task, "context_id", None):
                        _contexts[user_id] = task.context_id
                if isinstance(update, TaskArtifactUpdateEvent):
                    got_artifact_update = True
                    parts.extend(_extract_parts(update.artifact.parts))

        # Non-streaming fallback: pull parts from the final task's artifacts.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
