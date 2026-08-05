"""TickerMaster - Support Ticket System built with Streamlit."""

import streamlit as st
from pydantic import ValidationError

from config import settings
from database import (
    DatabaseError,
    TicketNotFoundError,
    create_message,
    create_ticket,
    delete_ticket,
    get_messages,
    get_ticket_by_id,
    get_ticket_stats,
    get_tickets,
    update_ticket,
)
from models import MessageCreate, TicketCreate, TicketUpdate

# Page configuration
st.set_page_config(
    page_title=settings.app_title,
    page_icon=settings.page_icon,
    layout="wide",
)


def show_dashboard():
    """Display ticket statistics dashboard."""
    st.header("📊 Dashboard")

    try:
        stats = get_ticket_stats()

        # Top-level metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("🎫 Total Tickets", stats.total)
        col2.metric("🔓 Open", stats.open)
        col3.metric("⏳ In Progress", stats.in_progress)
        col4.metric("✅ Resolved", stats.resolved)
        col5.metric("🔒 Closed", stats.closed)

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Tickets by Status")
            if stats.total > 0:
                status_data = {
                    "Open": stats.open,
                    "In Progress": stats.in_progress,
                    "Resolved": stats.resolved,
                    "Closed": stats.closed,
                }
                st.bar_chart(status_data)
            else:
                st.info("No tickets yet")

        with col2:
            st.subheader("Tickets by Priority")
            if stats.by_priority:
                st.bar_chart(stats.by_priority)
            else:
                st.info("No priority data available")

        # Category breakdown
        if stats.by_category:
            st.subheader("Tickets by Category")
            st.bar_chart(stats.by_category)

    except DatabaseError as e:
        st.error(f"❌ Database Error: {e}")
        st.info("Please check your database connection.")
    except Exception as e:
        st.error(f"❌ Unexpected Error: {e}")


def show_ticket_list():
    """Display filterable list of tickets."""
    st.header("🎫 All Tickets")

    # Filters in sidebar
    with st.sidebar:
        st.subheader("🔍 Filters")
        status_filter = st.selectbox(
            "Status",
            [None, "open", "in_progress", "resolved", "closed"],
            format_func=lambda x: "All" if x is None else x.replace("_", " ").title(),
        )
        priority_filter = st.selectbox(
            "Priority",
            [None, "low", "medium", "high", "urgent"],
            format_func=lambda x: "All" if x is None else x.title(),
        )
        category_filter = st.selectbox(
            "Category",
            [None, "bug", "feature", "support", "question", "other"],
            format_func=lambda x: "All" if x is None else x.title(),
        )

    try:
        tickets = get_tickets(
            status=status_filter, priority=priority_filter, category=category_filter
        )

        if not tickets:
            st.info("📋 No tickets found with the selected filters.")
            return

        st.write(f"Found **{len(tickets)}** ticket(s)")

        # Display tickets in a table
        for ticket in tickets:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

                with col1:
                    st.write(f"**{ticket.title}**")
                    st.caption(f"ID: {ticket.ticket_id}")

                with col2:
                    status_emoji = {
                        "open": "🔓",
                        "in_progress": "⏳",
                        "resolved": "✅",
                        "closed": "🔒",
                    }
                    st.write(f"{status_emoji.get(ticket.status, '')} {ticket.status}")

                with col3:
                    priority_emoji = {
                        "low": "🟢",
                        "medium": "🟡",
                        "high": "🟠",
                        "urgent": "🔴",
                    }
                    st.write(f"{priority_emoji.get(ticket.priority, '')} {ticket.priority}")

                with col4:
                    st.write(f"${ticket.last_price:.2f}")

                with col5:
                    if st.button("👁️ View", key=f"view_{ticket.ticket_id}"):
                        st.session_state.current_ticket = ticket.ticket_id
                        st.session_state.page = "Ticket Detail"
                        st.rerun()

                st.divider()

    except DatabaseError as e:
        st.error(f"❌ Database Error: {e}")
    except Exception as e:
        st.error(f"❌ Unexpected Error: {e}")


def show_ticket_detail(ticket_id: str):
    """Display single ticket with messages and update capabilities."""
    try:
        ticket = get_ticket_by_id(ticket_id)

        # Header with back button
        col1, col2 = st.columns([6, 1])
        with col1:
            st.header(f"🎫 {ticket.title}")
        with col2:
            if st.button("← Back"):
                st.session_state.page = "All Tickets"
                st.rerun()

        # Ticket information
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Status", ticket.status.replace("_", " ").title())
        col2.metric("Priority", ticket.priority.title())
        col3.metric("Category", ticket.category.title() if ticket.category else "N/A")
        col4.metric("Last Price", f"${ticket.last_price:.2f}")

        st.caption(f"Created by {ticket.created_by} on {ticket.created_at.strftime('%Y-%m-%d %H:%M')}")
        if ticket.updated_at:
            st.caption(f"Last updated: {ticket.updated_at.strftime('%Y-%m-%d %H:%M')}")

        st.divider()

        # Quick status update buttons
        st.subheader("⚡ Quick Actions")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("🔓 Mark Open"):
                try:
                    update_ticket(ticket_id, TicketUpdate(status="open"))
                    st.success("Status updated!")
                    st.rerun()
                except (ValidationError, DatabaseError) as e:
                    st.error(f"Error: {e}")

        with col2:
            if st.button("⏳ Mark In Progress"):
                try:
                    update_ticket(ticket_id, TicketUpdate(status="in_progress"))
                    st.success("Status updated!")
                    st.rerun()
                except (ValidationError, DatabaseError) as e:
                    st.error(f"Error: {e}")

        with col3:
            if st.button("✅ Mark Resolved"):
                try:
                    update_ticket(ticket_id, TicketUpdate(status="resolved"))
                    st.success("Status updated!")
                    st.rerun()
                except (ValidationError, DatabaseError) as e:
                    st.error(f"Error: {e}")

        with col4:
            if st.button("🔒 Mark Closed"):
                try:
                    update_ticket(ticket_id, TicketUpdate(status="closed"))
                    st.success("Status updated!")
                    st.rerun()
                except (ValidationError, DatabaseError) as e:
                    st.error(f"Error: {e}")

        st.divider()

        # Edit ticket details
        with st.expander("✏️ Edit Ticket Details"):
            with st.form("edit_ticket"):
                new_title = st.text_input("Title", value=ticket.title)
                new_priority = st.selectbox(
                    "Priority",
                    ["low", "medium", "high", "urgent"],
                    index=["low", "medium", "high", "urgent"].index(ticket.priority),
                )
                new_category = st.selectbox(
                    "Category",
                    [None, "bug", "feature", "support", "question", "other"],
                    index=(
                        [None, "bug", "feature", "support", "question", "other"].index(
                            ticket.category
                        )
                        if ticket.category
                        else 0
                    ),
                    format_func=lambda x: "None" if x is None else x.title(),
                )
                new_price = st.number_input(
                    "Last Price", value=float(ticket.last_price), min_value=0.0, step=0.01
                )

                if st.form_submit_button("Save Changes", type="primary"):
                    try:
                        # Only update changed fields
                        updates = {}
                        if new_title != ticket.title:
                            updates["title"] = new_title
                        if new_priority != ticket.priority:
                            updates["priority"] = new_priority
                        if new_category != ticket.category:
                            updates["category"] = new_category
                        if new_price != ticket.last_price:
                            updates["last_price"] = new_price

                        if updates:
                            update_ticket(ticket_id, TicketUpdate(**updates))
                            st.success("✅ Ticket updated successfully!")
                            st.rerun()
                        else:
                            st.info("No changes detected.")

                    except ValidationError as e:
                        st.error("❌ Validation Error:")
                        for error in e.errors():
                            field = " → ".join(str(x) for x in error["loc"])
                            st.error(f"**{field}**: {error['msg']}")
                    except DatabaseError as e:
                        st.error(f"❌ Database Error: {e}")

        # Delete button
        with st.expander("🗑️ Delete Ticket"):
            st.warning(
                "⚠️ **Warning:** This will permanently delete the ticket and all its messages."
            )
            confirm_delete = st.text_input(
                "Type the ticket ID to confirm deletion:", key="delete_confirm"
            )
            if st.button("Delete Permanently", type="secondary"):
                if confirm_delete == ticket_id:
                    try:
                        delete_ticket(ticket_id)
                        st.success("✅ Ticket deleted successfully!")
                        st.session_state.page = "All Tickets"
                        st.rerun()
                    except (TicketNotFoundError, DatabaseError) as e:
                        st.error(f"❌ Error deleting ticket: {e}")
                else:
                    st.error("❌ Ticket ID doesn't match. Deletion cancelled.")

        st.divider()

        # Messages section
        st.subheader("💬 Messages")

        try:
            messages = get_messages(ticket_id)

            if messages:
                for msg in messages:
                    with st.chat_message("user"):
                        st.write(f"**{msg.author}** - {msg.created_at.strftime('%Y-%m-%d %H:%M')}")
                        st.write(msg.message_text)
            else:
                st.info("No messages yet.")

            # Add new message form
            with st.form("add_message", clear_on_submit=True):
                st.write("**Add a message**")
                message_text = st.text_area(
                    "Message", placeholder="Type your message here...", height=100
                )
                author = st.text_input("Your Name", placeholder="John Doe")

                if st.form_submit_button("➡️ Send", type="primary"):
                    try:
                        message_data = MessageCreate(message_text=message_text, author=author)
                        create_message(ticket_id, message_data)
                        st.success("✅ Message added!")
                        st.rerun()

                    except ValidationError as e:
                        st.error("❌ Validation Error:")
                        for error in e.errors():
                            field = " → ".join(str(x) for x in error["loc"])
                            st.error(f"**{field}**: {error['msg']}")
                    except DatabaseError as e:
                        st.error(f"❌ Database Error: {e}")

        except DatabaseError as e:
            st.error(f"❌ Error loading messages: {e}")

    except TicketNotFoundError as e:
        st.error(f"❌ {e}")
        st.info("The ticket may have been deleted or the ID is incorrect.")
        if st.button("← Back to All Tickets"):
            st.session_state.page = "All Tickets"
            st.rerun()

    except DatabaseError as e:
        st.error(f"❌ Database Error: {e}")
        if st.button("← Back to All Tickets"):
            st.session_state.page = "All Tickets"
            st.rerun()

    except Exception as e:
        st.error(f"❌ Unexpected Error: {e}")


def show_create_ticket_form():
    """Display form to create a new ticket with error handling."""
    st.header("➕ Create New Ticket")

    with st.form("create_ticket", clear_on_submit=True):
        title = st.text_input(
            "Ticker Symbol *",
            placeholder="e.g., AAPL, MSFT, GOOGL",
            help="Stock ticker symbol (3-200 characters, will be converted to uppercase)",
        )

        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Status", ["open", "in_progress", "resolved", "closed"])
            priority = st.selectbox("Priority", ["low", "medium", "high", "urgent"], index=1)

        with col2:
            category = st.selectbox(
                "Category",
                [None, "bug", "feature", "support", "question", "other"],
                format_func=lambda x: "Select category" if x is None else x.title(),
            )

        last_price = st.number_input(
            "Last Price *",
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            help="Stock last price (required, can be 0)",
        )

        created_by = st.text_input(
            "Created By *", placeholder="Your name", help="Your name (2-100 characters)"
        )

        submit = st.form_submit_button("Create Ticket", type="primary")

        if submit:
            try:
                ticket_data = TicketCreate(
                    title=title,
                    status=status,
                    priority=priority,
                    category=category if category else None,
                    created_by=created_by,
                    last_price=last_price,
                )
                new_ticket = create_ticket(ticket_data)
                # On mémorise le ticket créé pour l'afficher HORS du form
                st.session_state.last_created_ticket = new_ticket

            except ValidationError as e:
                st.error("❌ Validation Error: Please fix the following issues:")
                for error in e.errors():
                    field = " → ".join(str(x) for x in error["loc"])
                    st.error(f"**{field}**: {error['msg']}")
            except DatabaseError as e:
                st.error(f"❌ Database Error: {e}")
                st.info("Please try again or contact support if the issue persists.")
            except Exception as e:
                st.error(f"❌ Unexpected Error: {e}")

    # --- HORS du bloc `with st.form(...)` (indentation au niveau de la fonction) ---
    new_ticket = st.session_state.get("last_created_ticket")
    if new_ticket:
        st.success(f"✅ Ticket **{new_ticket.ticket_id}** created successfully!")
        st.balloons()

        with st.expander("View Created Ticket"):
            st.json(new_ticket.model_dump(mode="json"), expanded=True)

        if st.button("View Ticket Details"):
            st.session_state.current_ticket = new_ticket.ticket_id
            st.session_state.page = "Ticket Detail"
            st.session_state.last_created_ticket = None  # nettoyage
            st.rerun()


def main():
    """Main application entry point."""
    st.title(settings.app_title)

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"
    if "current_ticket" not in st.session_state:
        st.session_state.current_ticket = None

    PAGES = ["Dashboard", "All Tickets", "Create Ticket"]

    def on_nav_change():
        # Un clic sur le radio quitte toujours le détail et impose la page choisie
        st.session_state.page = st.session_state.nav_radio
        st.session_state.current_ticket = None

    with st.sidebar:
        st.header("🧭 Navigation")

        # Le radio suit la page courante quand elle fait partie des 3 principales,
        # sinon (Ticket Detail) on le laisse sur son dernier choix sans forcer d'index.
        default_index = PAGES.index(st.session_state.page) if st.session_state.page in PAGES else 0
        st.radio("Go to", PAGES, index=default_index, key="nav_radio", on_change=on_nav_change)

        st.divider()

        with st.expander("🔗 Connection Info"):
            st.write(f"**Host:** {settings.db_host}")
            st.write(f"**Database:** {settings.db_name}")
            st.write(f"**User:** {settings.db_user or 'Not configured'}")

    # Routage
    if st.session_state.page == "Dashboard":
        show_dashboard()
    elif st.session_state.page == "All Tickets":
        show_ticket_list()
    elif st.session_state.page == "Create Ticket":
        show_create_ticket_form()
    elif st.session_state.page == "Ticket Detail" and st.session_state.current_ticket:
        show_ticket_detail(st.session_state.current_ticket)
    else:
        st.session_state.page = "Dashboard"
        st.rerun()


if __name__ == "__main__":
    main()
