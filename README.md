# TickerMaster

A modern support ticket system for stock tickers built with Streamlit and Lakebase Postgres in Databricks Apps

## Features

✅ **View all support tickets** with filtering by status, priority, and category  
✅ **Create new tickets** with ticker symbols and stock prices  
✅ **View ticket details** with full message history  
✅ **Update ticket status** with quick action buttons  
✅ **Add messages** to tickets with threaded conversations  
✅ **Delete tickets** with confirmation (permanently removes ticket and messages)  
✅ **Dashboard statistics** with charts and metrics  
✅ **Type-safe** with Pydantic models and full type hints  
✅ **Input validation** with helpful error messages  
✅ **Managed with uv** for fast, reliable dependency management

## Tech Stack

- **Databricks**
- **Frontend:** Streamlit 1.32+
- **Backend:** Lakebase Postgres (Databricks)
- **Validation:** Pydantic 2.6+
- **Package Manager:** uv
- **Linting:** Ruff
- **Type Checking:** Python 3.12 type hints

## Project Structure

```
databricks-agent/
├── pyproject.toml       # uv dependency management + ruff config
├── app.yaml            # Databricks app configuration
├── .env.example        # Environment variables template
├── config.py           # Settings with Pydantic
├── models.py           # Pydantic models with type hints
├── database.py         # Database operations with error handling
└── app.py              # Main Streamlit application
```

## Setup

### 1. Prerequisites

- Python 3.12+
- uv installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Access to Lakebase Postgres database (`ticketing-support`)

### 2. Database Schema

Ensure your Lakebase database has these tables:

```sql
-- Tickets table
CREATE TABLE tickets (
    ticket_id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    priority VARCHAR DEFAULT 'medium',
    category VARCHAR,
    created_by VARCHAR NOT NULL,
    last_price NUMERIC NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

-- Messages table
CREATE TABLE ticket_messages (
    message_id VARCHAR PRIMARY KEY,
    ticket_id VARCHAR NOT NULL,
    message_text VARCHAR,
    author VARCHAR,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);
```

### 3. Configure Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your Lakebase credentials:

```env
DB_HOST=instance-eu2j.cloud.databricks.com
DB_PORT=5432
DB_NAME=databricks_postgres
DB_USER=your_email@databricks.com
DB_PASSWORD=your_password
```

### 4. Install Dependencies

```bash
uv sync
```

### 5. Run Locally (Development)

```bash
uv run streamlit run app.py
```

### 6. Deploy to Databricks Apps

```bash
# Check app status
databricks apps get tickermaster --output JSON

# If stopped, start it
databricks apps start tickermaster --timeout 20m

# Deploy
databricks apps deploy tickermaster \
  --source-code-path /Workspace/Users/your_email@databricks.com/databricks-agent \
  --output JSON
```

## Usage

### Dashboard
View ticket statistics with charts showing:
- Total tickets by status
- Tickets by priority
- Tickets by category

### All Tickets
Browse and filter tickets by:
- Status (open, in_progress, resolved, closed)
- Priority (low, medium, high, urgent)
- Category (bug, feature, support, question, other)

### Create Ticket
Create new tickets with:
- Ticker symbol (e.g., AAPL, MSFT)
- Status and priority
- Category
- Last stock price
- Creator name

### Ticket Detail
- View full ticket information
- Quick status update buttons
- Edit ticket details (title, priority, category, price)
- Add messages to the conversation
- Delete ticket with confirmation

## Data Models

### Ticket
- `ticket_id`: Unique identifier (auto-generated)
- `title`: Ticker symbol (3-200 chars, uppercase)
- `status`: open | in_progress | resolved | closed
- `priority`: low | medium | high | urgent
- `category`: bug | feature | support | question | other (optional)
- `created_by`: Creator name (2-100 chars)
- `last_price`: Stock price (required, >= 0)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Message
- `message_id`: Unique identifier (auto-generated)
- `ticket_id`: Associated ticket
- `message_text`: Message content (1-5000 chars)
- `author`: Message author (2-100 chars)
- `created_at`: Creation timestamp

## Error Handling

The app has comprehensive error handling:
- **Pydantic validation** catches invalid inputs before database operations
- **Custom database exceptions** provide clear error messages
- **User-friendly error display** in the Streamlit UI
- **Transaction rollback** on database errors

## Code Quality

### Type Safety
Full type hints throughout the codebase:
```python
def get_ticket_by_id(ticket_id: str) -> Ticket:
    ...
```

### Validation
Automatic Pydantic validation:
```python
# This raises ValidationError automatically
TicketCreate(title="AB", last_price=-10)  # Too short, negative price
```

### Linting
Ruff configured for:
- Import sorting
- Code formatting
- Error detection
- Best practices

Run linting:
```bash
uv run ruff check .
uv run ruff format .
```

## Development

### Add New Feature
1. Update models in `models.py`
2. Add database operations in `database.py`
3. Create UI in `app.py`
4. Test thoroughly
5. Commit to Git

### Debug
- Check Streamlit logs in the app
- Use `st.exception()` for detailed error traces
- Verify database connection in sidebar
