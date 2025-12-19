"""Session management service using DynamoDB or SQLite."""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from server.config import get_settings
from server.models.sessions import (
    MessageRole,
    MessageSource,
    Session,
    SessionArtifact,
    SessionDetail,
    SessionMessage,
    SessionStatus,
    SessionSummary,
)

logger = logging.getLogger(__name__)


class SQLiteSessionStore:
    """SQLite-based session storage for local development."""

    def __init__(self, db_path: str = "sessions.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created TEXT NOT NULL,
                    updated TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    message_count INTEGER DEFAULT 0,
                    preview TEXT DEFAULT '',
                    artifacts TEXT DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT DEFAULT 'text',
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON sessions(updated DESC)
            """)
            conn.commit()
        logger.info(f"SQLite session store initialized at {self.db_path}")

    def create_session(self, session: Session) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (id, name, created, updated, status, message_count, preview, artifacts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session.id,
                    session.name,
                    session.created.isoformat(),
                    session.updated.isoformat(),
                    session.status.value,
                    session.message_count,
                    session.preview,
                    json.dumps([]),
                ),
            )
            conn.commit()

    def get_session(self, session_id: str) -> SessionDetail | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None

            messages = []
            msg_rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
            for msg in msg_rows:
                messages.append(
                    SessionMessage(
                        timestamp=datetime.fromisoformat(msg["timestamp"]),
                        role=MessageRole(msg["role"]),
                        content=msg["content"],
                        source=MessageSource(msg["source"]),
                    )
                )

            artifacts = []
            for a in json.loads(row["artifacts"] or "[]"):
                artifacts.append(
                    SessionArtifact(
                        path=a["path"],
                        created=datetime.fromisoformat(a["created"]),
                        type=a["type"],
                        size=a["size"],
                    )
                )

            return SessionDetail(
                id=row["id"],
                name=row["name"],
                created=datetime.fromisoformat(row["created"]),
                updated=datetime.fromisoformat(row["updated"]),
                status=SessionStatus(row["status"]),
                message_count=row["message_count"],
                preview=row["preview"] or "",
                artifacts=artifacts,
                messages=messages,
            )

    def list_sessions(self, limit: int = 20) -> list[SessionSummary]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, name, created, updated, message_count, preview "
                "FROM sessions ORDER BY updated DESC LIMIT ?",
                (limit,),
            ).fetchall()

            return [
                SessionSummary(
                    id=row["id"],
                    name=row["name"],
                    created=datetime.fromisoformat(row["created"]),
                    updated=datetime.fromisoformat(row["updated"]),
                    message_count=row["message_count"],
                    preview=row["preview"] or "",
                )
                for row in rows
            ]

    def add_message(self, session_id: str, message: SessionMessage) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, timestamp, role, content, source) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    message.timestamp.isoformat(),
                    message.role.value,
                    message.content,
                    message.source.value,
                ),
            )
            # Update session
            update_sql = """
                UPDATE sessions
                SET updated = ?, message_count = message_count + 1
                WHERE id = ?
            """
            conn.execute(update_sql, (message.timestamp.isoformat(), session_id))

            # Set preview if first user message
            if message.role == MessageRole.USER:
                conn.execute(
                    "UPDATE sessions SET preview = ? WHERE id = ? AND preview = ''",
                    (message.content[:100], session_id),
                )
            conn.commit()

    def update_session_name(self, session_id: str, name: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE sessions SET name = ? WHERE id = ?", (name, session_id))
            conn.commit()

    def delete_session(self, session_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            result = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            return result.rowcount > 0

    def add_artifact(self, session_id: str, artifact: SessionArtifact) -> None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT artifacts FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row:
                artifacts = json.loads(row[0] or "[]")
                artifacts.append(
                    {
                        "path": artifact.path,
                        "created": artifact.created.isoformat(),
                        "type": artifact.type,
                        "size": artifact.size,
                    }
                )
                conn.execute(
                    "UPDATE sessions SET artifacts = ? WHERE id = ?",
                    (json.dumps(artifacts), session_id),
                )
                conn.commit()

    def get_session_for_artifact(self, artifact_path: str) -> str | None:
        """Find which session created an artifact by scanning all sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, artifacts FROM sessions").fetchall()
            for row in rows:
                artifacts = json.loads(row["artifacts"] or "[]")
                for a in artifacts:
                    if a.get("path") == artifact_path:
                        return row["id"]
        return None


class SessionService:
    """Manages conversation sessions in DynamoDB or SQLite.

    Storage priority:
    1. DynamoDB (if DYNAMODB_SESSIONS_TABLE is set)
    2. SQLite (local file, persistent across restarts)

    Uses a single-table design with composite keys for DynamoDB:
    - PK: SESSION#{id} or ARTIFACT#{path}
    - SK: META, MSG#{timestamp}, or SESSION#{id}
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.table_name = settings.dynamodb_sessions_table
        self.region = settings.aws_region
        self._table = None
        self._sqlite: SQLiteSessionStore | None = None
        self._local_sessions: dict[str, SessionDetail] = {}

        if self.table_name:
            try:
                dynamodb = boto3.resource("dynamodb", region_name=self.region)
                self._table = dynamodb.Table(self.table_name)
                logger.info(f"Connected to DynamoDB table: {self.table_name}")
            except Exception as e:
                logger.error(f"Failed to connect to DynamoDB: {e}")
        else:
            # Use SQLite for local persistence
            workspace = os.getenv("WORKSPACE", "/workspace")
            db_path = os.path.join(workspace, "sessions.db")
            try:
                self._sqlite = SQLiteSessionStore(db_path)
                logger.info(f"Using SQLite session store at {db_path}")
            except Exception as e:
                logger.error(f"Failed to initialize SQLite: {e}")
                logger.warning("Falling back to in-memory storage")

    @property
    def is_persistent(self) -> bool:
        """Check if using persistent storage (DynamoDB or SQLite) vs in-memory."""
        return self._table is not None or self._sqlite is not None

    @property
    def storage_type(self) -> str:
        """Get the current storage backend type."""
        if self._table:
            return "dynamodb"
        elif self._sqlite:
            return "sqlite"
        else:
            return "in-memory"

    async def create_session(self, name: str | None = None) -> Session:
        """Create a new session."""
        session = Session(
            id=str(uuid.uuid4()),
            name=name or "New Session",
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        )

        if self._table:
            now_iso = session.updated.isoformat()
            try:
                self._table.put_item(
                    Item={
                        "PK": f"SESSION#{session.id}",
                        "SK": "META",
                        "id": session.id,
                        "name": session.name,
                        "created": session.created.isoformat(),
                        "updated": now_iso,
                        "status": session.status.value,
                        "message_count": 0,
                        "artifacts": [],
                        "preview": "",
                        # GSI1 for listing sessions
                        "GSI1PK": "USER#default",
                        "GSI1SK": f"updated#{now_iso}",
                    }
                )
            except ClientError as e:
                logger.error(f"Failed to create session in DynamoDB: {e}")
                raise
        elif self._sqlite:
            # SQLite persistence
            self._sqlite.create_session(session)
        else:
            # In-memory fallback
            self._local_sessions[session.id] = SessionDetail(**session.model_dump(), messages=[])

        return session

    async def get_session(self, session_id: str) -> SessionDetail | None:
        """Get a session with all its messages."""
        if self._table:
            try:
                # Get metadata
                meta_response = self._table.get_item(
                    Key={"PK": f"SESSION#{session_id}", "SK": "META"}
                )
                if "Item" not in meta_response:
                    return None

                meta = meta_response["Item"]

                # Get messages
                msg_response = self._table.query(
                    KeyConditionExpression=Key("PK").eq(f"SESSION#{session_id}")
                    & Key("SK").begins_with("MSG#")
                )

                messages = []
                for item in msg_response.get("Items", []):
                    messages.append(
                        SessionMessage(
                            timestamp=datetime.fromisoformat(item["timestamp"]),
                            role=MessageRole(item["role"]),
                            content=item["content"],
                            source=MessageSource(item.get("source", "text")),
                        )
                    )

                # Parse artifacts
                artifacts = []
                for a in meta.get("artifacts", []):
                    artifacts.append(
                        SessionArtifact(
                            path=a["path"],
                            created=datetime.fromisoformat(a["created"]),
                            type=a["type"],
                            size=a["size"],
                        )
                    )

                return SessionDetail(
                    id=meta["id"],
                    name=meta["name"],
                    created=datetime.fromisoformat(meta["created"]),
                    updated=datetime.fromisoformat(meta["updated"]),
                    status=SessionStatus(meta["status"]),
                    message_count=int(meta["message_count"]),
                    artifacts=artifacts,
                    preview=meta.get("preview", ""),
                    messages=sorted(messages, key=lambda m: m.timestamp),
                )
            except ClientError as e:
                logger.error(f"Failed to get session from DynamoDB: {e}")
                return None
        elif self._sqlite:
            return self._sqlite.get_session(session_id)
        else:
            return self._local_sessions.get(session_id)

    async def list_sessions(
        self, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[SessionSummary], str | None]:
        """List sessions, most recent first."""
        if self._table:
            try:
                query_params = {
                    "IndexName": "GSI1",
                    "KeyConditionExpression": Key("GSI1PK").eq("USER#default"),
                    "ScanIndexForward": False,  # Descending order (most recent first)
                    "Limit": limit,
                }

                if cursor:
                    query_params["ExclusiveStartKey"] = {
                        "GSI1PK": "USER#default",
                        "GSI1SK": cursor,
                        "PK": f"SESSION#{cursor.split('#')[1] if '#' in cursor else ''}",
                        "SK": "META",
                    }

                response = self._table.query(**query_params)

                sessions = []
                for item in response.get("Items", []):
                    sessions.append(
                        SessionSummary(
                            id=item["id"],
                            name=item["name"],
                            created=datetime.fromisoformat(item["created"]),
                            updated=datetime.fromisoformat(item["updated"]),
                            message_count=int(item["message_count"]),
                            preview=item.get("preview", ""),
                        )
                    )

                next_cursor = None
                if "LastEvaluatedKey" in response:
                    next_cursor = response["LastEvaluatedKey"].get("GSI1SK")

                return sessions, next_cursor
            except ClientError as e:
                logger.error(f"Failed to list sessions from DynamoDB: {e}")
                return [], None
        elif self._sqlite:
            # SQLite persistence (no cursor support)
            return self._sqlite.list_sessions(limit), None
        else:
            # In-memory fallback
            sessions = [
                SessionSummary(
                    id=s.id,
                    name=s.name,
                    created=s.created,
                    updated=s.updated,
                    message_count=s.message_count,
                    preview=s.preview,
                )
                for s in self._local_sessions.values()
            ]
            # Sort by updated descending
            sessions.sort(key=lambda s: s.updated, reverse=True)
            return sessions[:limit], None

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        source: MessageSource = MessageSource.TEXT,
    ) -> SessionMessage:
        """Add a message to a session."""
        timestamp = datetime.utcnow()
        message = SessionMessage(
            timestamp=timestamp,
            role=role,
            content=content,
            source=source,
        )

        if self._table:
            ts_iso = timestamp.isoformat()
            try:
                # Add message item
                self._table.put_item(
                    Item={
                        "PK": f"SESSION#{session_id}",
                        "SK": f"MSG#{ts_iso}",
                        "timestamp": ts_iso,
                        "role": role.value,
                        "content": content,
                        "source": source.value,
                    }
                )

                # Update session metadata
                update_expr = (
                    "SET updated = :updated, message_count = message_count + :inc, GSI1SK = :gsi1sk"
                )
                expr_values = {
                    ":updated": ts_iso,
                    ":inc": 1,
                    ":gsi1sk": f"updated#{ts_iso}",
                }

                # Set preview from first user message
                if role == MessageRole.USER:
                    update_expr += ", preview = if_not_exists(preview, :empty_str)"
                    update_expr = update_expr.replace(
                        "if_not_exists(preview, :empty_str)",
                        ":preview",
                    )
                    # Only set preview if empty
                    try:
                        self._table.update_item(
                            Key={"PK": f"SESSION#{session_id}", "SK": "META"},
                            UpdateExpression=(
                                "SET updated = :updated, "
                                "message_count = message_count + :inc, "
                                "GSI1SK = :gsi1sk, "
                                "preview = if_not_exists(preview, :preview)"
                            ),
                            ConditionExpression="attribute_exists(PK)",
                            ExpressionAttributeValues={
                                ":updated": ts_iso,
                                ":inc": 1,
                                ":gsi1sk": f"updated#{ts_iso}",
                                ":preview": content[:100],
                            },
                        )
                    except ClientError:
                        # Preview already set, just update without preview
                        self._table.update_item(
                            Key={"PK": f"SESSION#{session_id}", "SK": "META"},
                            UpdateExpression=update_expr,
                            ExpressionAttributeValues=expr_values,
                        )
                else:
                    self._table.update_item(
                        Key={"PK": f"SESSION#{session_id}", "SK": "META"},
                        UpdateExpression=update_expr,
                        ExpressionAttributeValues=expr_values,
                    )
            except ClientError as e:
                logger.error(f"Failed to add message to DynamoDB: {e}")
                raise
        elif self._sqlite:
            # SQLite persistence
            self._sqlite.add_message(session_id, message)
        else:
            # In-memory fallback
            if session_id in self._local_sessions:
                session = self._local_sessions[session_id]
                session.messages.append(message)
                session.message_count += 1
                session.updated = timestamp
                if role == MessageRole.USER and not session.preview:
                    session.preview = content[:100]

        return message

    async def update_session_name(self, session_id: str, name: str) -> None:
        """Update a session's name."""
        if self._table:
            try:
                self._table.update_item(
                    Key={"PK": f"SESSION#{session_id}", "SK": "META"},
                    UpdateExpression="SET #name = :name",
                    ExpressionAttributeNames={"#name": "name"},
                    ExpressionAttributeValues={":name": name},
                )
            except ClientError as e:
                logger.error(f"Failed to update session name: {e}")
                raise
        elif self._sqlite:
            self._sqlite.update_session_name(session_id, name)
        else:
            if session_id in self._local_sessions:
                self._local_sessions[session_id].name = name

    async def add_artifact(self, session_id: str, artifact: SessionArtifact) -> None:
        """Track an artifact created during a session."""
        if self._table:
            artifact_dict = {
                "path": artifact.path,
                "created": artifact.created.isoformat(),
                "type": artifact.type,
                "size": artifact.size,
            }
            try:
                # Add to session's artifact list
                self._table.update_item(
                    Key={"PK": f"SESSION#{session_id}", "SK": "META"},
                    UpdateExpression=(
                        "SET artifacts = list_append(if_not_exists(artifacts, :empty), :artifact)"
                    ),
                    ExpressionAttributeValues={
                        ":artifact": [artifact_dict],
                        ":empty": [],
                    },
                )

                # Create reverse lookup (file → session)
                self._table.put_item(
                    Item={
                        "PK": f"ARTIFACT#{artifact.path}",
                        "SK": f"SESSION#{session_id}",
                        "created": artifact.created.isoformat(),
                        "type": artifact.type,
                        "size": artifact.size,
                    }
                )
            except ClientError as e:
                logger.error(f"Failed to add artifact: {e}")
                raise
        elif self._sqlite:
            self._sqlite.add_artifact(session_id, artifact)
        else:
            if session_id in self._local_sessions:
                self._local_sessions[session_id].artifacts.append(artifact)

    async def get_session_for_artifact(self, artifact_path: str) -> str | None:
        """Get the session ID that created an artifact."""
        if self._table:
            try:
                response = self._table.query(
                    KeyConditionExpression=Key("PK").eq(f"ARTIFACT#{artifact_path}"),
                    Limit=1,
                )
                if response.get("Items"):
                    # SK is SESSION#{id}
                    sk = response["Items"][0]["SK"]
                    return sk.replace("SESSION#", "")
            except ClientError as e:
                logger.error(f"Failed to get session for artifact: {e}")
        elif self._sqlite:
            return self._sqlite.get_session_for_artifact(artifact_path)
        else:
            for session_id, session in self._local_sessions.items():
                for artifact in session.artifacts:
                    if artifact.path == artifact_path:
                        return session_id
        return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        if self._table:
            try:
                # Query all items for this session
                response = self._table.query(
                    KeyConditionExpression=Key("PK").eq(f"SESSION#{session_id}")
                )

                # Batch delete
                with self._table.batch_writer() as batch:
                    for item in response.get("Items", []):
                        batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

                return True
            except ClientError as e:
                logger.error(f"Failed to delete session: {e}")
                return False
        elif self._sqlite:
            return self._sqlite.delete_session(session_id)
        else:
            if session_id in self._local_sessions:
                del self._local_sessions[session_id]
                return True
            return False

    async def fork_session(self, from_session_id: str, name: str | None = None) -> Session | None:
        """Create a new session as a copy of an existing one."""
        original = await self.get_session(from_session_id)
        if not original:
            return None

        new_session = await self.create_session(name=name or f"Fork of {original.name}")

        if self._table:
            try:
                # Copy messages
                with self._table.batch_writer() as batch:
                    for msg in original.messages:
                        ts_iso = msg.timestamp.isoformat()
                        batch.put_item(
                            Item={
                                "PK": f"SESSION#{new_session.id}",
                                "SK": f"MSG#{ts_iso}",
                                "timestamp": ts_iso,
                                "role": msg.role.value,
                                "content": msg.content,
                                "source": msg.source.value,
                            }
                        )

                # Update message count and preview
                self._table.update_item(
                    Key={"PK": f"SESSION#{new_session.id}", "SK": "META"},
                    UpdateExpression="SET message_count = :count, preview = :preview",
                    ExpressionAttributeValues={
                        ":count": len(original.messages),
                        ":preview": original.preview,
                    },
                )
            except ClientError as e:
                logger.error(f"Failed to fork session: {e}")
                raise
        elif self._sqlite:
            # SQLite: copy messages using existing methods
            for msg in original.messages:
                self._sqlite.add_message(new_session.id, msg)
            if original.preview:
                self._sqlite.update_session_name(new_session.id, new_session.name)
        else:
            # In-memory: copy messages
            if new_session.id in self._local_sessions:
                self._local_sessions[new_session.id].messages = list(original.messages)
                self._local_sessions[new_session.id].message_count = len(original.messages)
                self._local_sessions[new_session.id].preview = original.preview

        return new_session


# Singleton
_session_service: SessionService | None = None


def get_session_service() -> SessionService:
    """Get the session service singleton."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
