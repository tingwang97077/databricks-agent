"""Database operations with error handling and type safety."""

import os
import uuid
from contextlib import contextmanager
from typing import Optional

import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2 import IntegrityError, OperationalError
from psycopg2.extras import RealDictCursor

from config import settings
from models import (
    Message,
    MessageCreate,
    Ticket,
    TicketCreate,
    TicketStats,
    TicketUpdate,
)


class DatabaseError(Exception):
    """Custom database error for better error messages."""

    pass


class TicketNotFoundError(DatabaseError):
    """Raised when ticket doesn't exist."""

    pass


@contextmanager
def get_db_connection():
    w = WorkspaceClient()

    # Lakebase Autoscaling : le credential se génère à partir de l'ENDPOINT,
    # pas du nom de la base ni d'un nom d'instance.
    endpoint = os.environ.get("LAKEBASE_ENDPOINT")
    if not endpoint:
        pg = {k: v for k, v in os.environ.items() if k.startswith("PG") or "ENDPOINT" in k}
        raise DatabaseError(
            f"LAKEBASE_ENDPOINT absent. Vars présentes : {list(pg)}. "
            "Vérifie la clé de ressource (valueFrom) et redéploie."
        )
    cred = w.postgres.generate_database_credential(endpoint=endpoint)

    conn = psycopg2.connect(
        host=os.environ["PGHOST"],          # injecté par Databricks Apps
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ.get("PGDATABASE", "databricks_postgres"),
        user=os.environ["PGUSER"],          # injecté (client ID du service principal)
        password=cred.token,
        cursor_factory=RealDictCursor,
        sslmode=os.environ.get("PGSSLMODE", "require"),
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
) -> list[Ticket]:
    """
    Get all tickets with optional filtering.

    Args:
        status: Filter by status
        priority: Filter by priority
        category: Filter by category

    Returns:
        List of tickets

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM tickets WHERE 1=1"
            params = []

            if status:
                query += " AND status = %s"
                params.append(status)

            if priority:
                query += " AND priority = %s"
                params.append(priority)

            if category:
                query += " AND category = %s"
                params.append(category)

            query += " ORDER BY created_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [Ticket(**row) for row in rows]

    except Exception as e:
        raise DatabaseError(f"Error fetching tickets: {e}") from e


def get_ticket_by_id(ticket_id: str) -> Ticket:
    """
    Get a single ticket by ID.

    Args:
        ticket_id: The ticket ID

    Returns:
        Ticket object

    Raises:
        TicketNotFoundError: If ticket doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
            row = cursor.fetchone()

            if not row:
                raise TicketNotFoundError(f"Ticket {ticket_id} not found")

            return Ticket(**row)

    except TicketNotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error fetching ticket {ticket_id}: {e}") from e


def create_ticket(ticket: TicketCreate) -> Ticket:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Générer le prochain ticket_id (TICKET-001, TICKET-002, ...)
            cursor.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(ticket_id FROM 8) AS INTEGER)), 0) + 1 AS n "
                "FROM tickets WHERE ticket_id ~ '^TICKET-[0-9]+$'"
            )
            next_id = f"TICKET-{cursor.fetchone()['n']:03d}"

            cursor.execute(
                """
                INSERT INTO tickets
                    (ticket_id, title, status, priority, category, created_by, last_price, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING *
                """,
                (next_id, ticket.title, ticket.status, ticket.priority,
                 ticket.category, ticket.created_by, ticket.last_price),
            )
            return Ticket(**cursor.fetchone())
    except IntegrityError as e:
        raise DatabaseError(f"Database integrity error: {e}") from e
    except Exception as e:
        raise DatabaseError(f"Error creating ticket: {e}") from e


def update_ticket(ticket_id: str, update: TicketUpdate) -> Ticket:
    """
    Update a ticket.

    Args:
        ticket_id: The ticket ID
        update: Update data

    Returns:
        Updated ticket

    Raises:
        TicketNotFoundError: If ticket doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        # First verify ticket exists
        get_ticket_by_id(ticket_id)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Build dynamic update query
            update_data = update.model_dump(exclude_unset=True)
            if not update_data:
                return get_ticket_by_id(ticket_id)

            set_clause = ", ".join(f"{key} = %s" for key in update_data.keys())
            values = list(update_data.values()) + [ticket_id]

            cursor.execute(
                f"UPDATE tickets SET {set_clause} WHERE ticket_id = %s RETURNING *", values
            )
            row = cursor.fetchone()
            return Ticket(**row)

    except TicketNotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error updating ticket {ticket_id}: {e}") from e


def delete_ticket(ticket_id: str) -> None:
    """
    Delete a ticket.

    Args:
        ticket_id: The ticket ID

    Raises:
        TicketNotFoundError: If ticket doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        get_ticket_by_id(ticket_id)  # vérifie l'existence

        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Supprimer les messages enfants d'abord (contrainte FK)
            cursor.execute("DELETE FROM ticket_messages WHERE ticket_id = %s", (ticket_id,))
            # Puis le ticket lui-même
            cursor.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
    except TicketNotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error deleting ticket {ticket_id}: {e}") from e


def get_ticket_stats() -> TicketStats:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN status='open' THEN 1 ELSE 0 END),0) AS open,
                    COALESCE(SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END),0) AS in_progress,
                    COALESCE(SUM(CASE WHEN status='resolved' THEN 1 ELSE 0 END),0) AS resolved,
                    COALESCE(SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END),0) AS closed
                FROM tickets
            """)
            base = cursor.fetchone()

            cursor.execute("SELECT priority, COUNT(*) AS n FROM tickets GROUP BY priority")
            by_priority = {r["priority"]: r["n"] for r in cursor.fetchall()}

            cursor.execute("SELECT category, COUNT(*) AS n FROM tickets "
                           "WHERE category IS NOT NULL GROUP BY category")
            by_category = {r["category"]: r["n"] for r in cursor.fetchall()}

            return TicketStats(**base, by_priority=by_priority, by_category=by_category)
    except Exception as e:
        raise DatabaseError(f"Error fetching statistics: {e}") from e

def get_messages(ticket_id: int) -> list[Message]:
    """
    Get all messages for a ticket.

    Args:
        ticket_id: The ticket ID

    Returns:
        List of messages

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM ticket_messages WHERE ticket_id = %s ORDER BY created_at",
                (ticket_id,),
            )
            return [Message(**row) for row in cursor.fetchall()]
    except Exception as e:
        raise DatabaseError(f"Error fetching messages: {e}") from e


def create_message(ticket_id: str, message: MessageCreate) -> Message:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(message_id FROM 5) AS INTEGER)), 0) + 1 AS n "
                "FROM ticket_messages WHERE message_id ~ '^MSG-[0-9]+$'"
            )
            next_id = f"MSG-{cursor.fetchone()['n']:03d}"

            cursor.execute(
                """
                INSERT INTO ticket_messages
                    (message_id, ticket_id, author, message_text, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING *
                """,
                (next_id, ticket_id, message.author, message.message_text),
            )
            return Message(**cursor.fetchone())
    except IntegrityError as e:
        raise DatabaseError(f"Database integrity error: {e}") from e
    except Exception as e:
        raise DatabaseError(f"Error creating message: {e}") from e
