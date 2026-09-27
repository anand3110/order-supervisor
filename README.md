# Order Supervisor

A long-running AI supervisor that monitors a single customer order from creation to completion.

The supervisor reacts to order events, reasons about the current state, performs operational actions, sleeps until the next wake-up, and continues monitoring until the system determines that the run has reached a terminal state.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                          Next.js UI                              │
│   Dashboard   │   Run Details   │  Event Simulator │ Run Controls│
└───────────────────────────────┬───────────────────────────────--─┘
                                 │ HTTP
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                            FastAPI                                │
│         REST APIs   │   Run Lifecycle   │   Event Processing      │
└───────────────┬─────────────────────────────────────┬────────────┘
                │                                      │
                ▼                                      ▼
┌───────────────────────────┐            ┌──────────────────────────┐
│         PostgreSQL          │            │         Scheduler         │
│  Orders │ Runs │ Events      │            │  Finds sleeping runs      │
│  Activities │ Instructions   │            │  whose wake time has      │
│  Run State                   │            │  arrived                  │
└───────────────────────────┘            └────────────┬──────────────┘
                                                        │
                                                        ▼
                                          ┌──────────────────────────┐
                                          │    Supervisor Runtime      │
                                          └────────────┬──────────────┘
                                                        │
                                                        ▼
                                          ┌──────────────────────────┐
                                          │        Gemini LLM          │
                                          │  Reasoning │ Actions        │
                                          │  Sleep duration              │
                                          └────────────┬──────────────┘
                                                        │
                                                        ▼
                                          ┌──────────────────────────┐
                                          │     Action Services         │
                                          │  Fulfillment │ Payments      │
                                          │  Logistics │ Customer        │
                                          │  Internal Note                │
                                          └──────────────────────────┘
```

---

## How to Run

### Prerequisites

- Python 3.11+
- Node.js
- PostgreSQL
- Gemini API key

### 1. Clone the repository

```bash
git clone <your-github-repository-url>
cd order-supervisor
```

### 2. Start the backend

```bash
cd backend
python -m venv venv
```

**Windows:**

```bash
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:

```env
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/order_supervisor
GEMINI_API_KEY=<your-gemini-api-key>
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

- Backend: [http://localhost:8000](http://localhost:8000)
- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

- Frontend: [http://localhost:3000](http://localhost:3000)

---

## Demo Flow

1. Create a new order.
2. Start a supervisor run.
3. Inject `payment_confirmed`.
4. Add a run-specific instruction.
5. Inject `shipment_delayed`.
6. Inspect the supervisor reasoning and activities.
7. Inject `delivered`.
8. The backend completes the run.
9. Inspect the final summary, learnings, and recommendations.

---

## Technology Stack

| Layer     | Technology                                |
|-----------|--------------------------------------------|
| Frontend  | Next.js, React, TypeScript, Tailwind CSS   |
| Backend   | Python, FastAPI, SQLAlchemy                |
| Database  | PostgreSQL                                 |
| AI        | Google Gemini API                          |
| Runtime   | PostgreSQL-backed scheduler                |

---

## Project Structure

```text
order-supervisor/
├── backend/
├── frontend/
├── README.md
├── ARCHITECTURE.md
├── DESIGN.md
└── .gitignore
```