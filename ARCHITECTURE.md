# Architecture

## 1. Overview

The Order Supervisor is designed as a long-running process that supervises one order from creation until the order reaches a terminal state.

The main idea is that the supervisor does not continuously run in a loop making LLM calls. Instead, a run is persisted in PostgreSQL with its current state and next wake-up time.

When something important happens, such as a new order event, the supervisor can be woken up. Otherwise, the scheduler wakes it up when its scheduled wake-up time arrives.

The backend is responsible for the run lifecycle and completion. The LLM is only responsible for deciding what the supervisor should do next.

---

## 2. High-Level Architecture

```text
╔═══════════════════════════════════════════════════════════════╗
║                          Next.js UI                            ║
║  Dashboard   Run Details   Event Simulator   Run Controls      ║
╚════════════════════════════╤════════════════════════════════╝
                              │  HTTP
                              ▼
╔═══════════════════════════════════════════════════════════════╗
║                           FastAPI                               ║
║  Supervisor APIs   Order APIs   Run APIs   Event APIs           ║
╚═══════════════╤═══════════════════════════════╤═══════════════╝
                 │                               │
                 ▼                               ▼
   ┌───────────────────────────┐   ┌───────────────────────────┐
   │        PostgreSQL          │   │         Scheduler          │
   │ ─────────────────────────  │   │ ─────────────────────────  │
   │  Supervisors                │   │  Finds sleeping runs        │
   │  Orders                     │   │  whose wake time            │
   │  Runs                       │   │  has arrived                │
   │  Events                     │   └──────────────┬─────────────┘
   │  Activities                 │                  │
   │  Instructions               │                  │
   └──────────────┬─────────────┘                  │
                  │                                  │
                  └────────────────┬─────────────────┘
                                    ▼
                    ╔═══════════════════════════╗
                    ║     Supervisor Runtime      ║
                    ║ ───────────────────────────║
                    ║  Load state                  ║
                    ║  Process events               ║
                    ║  Call agent                    ║
                    ║  Execute actions                ║
                    ║  Update state                    ║
                    ║  Schedule next wake-up            ║
                    ╚══════════════╤════════════════╝
                                    │
                                    ▼
                    ╔═══════════════════════════╗
                    ║        Gemini API           ║
                    ║ ───────────────────────────║
                    ║  Reasoning                    ║
                    ║  Recommended actions            ║
                    ║  Sleep duration                    ║
                    ╚══════════════╤════════════════╝
                                    │
                                    ▼
                    ╔═══════════════════════════╗
                    ║      Action Services         ║
                    ║ ───────────────────────────║
                    ║  Fulfillment                  ║
                    ║  Payments                       ║
                    ║  Logistics                        ║
                    ║  Customer                           ║
                    ║  Internal Notes                       ║
                    ╚═══════════════════════════╝
```

---

## 3. Main Components

### 3.1 Next.js Frontend

The frontend provides the interface for creating and monitoring supervisor runs.

The main screens are:

- Dashboard
- Run details
- Event simulator
- Run-specific instructions
- Run controls
- Activity history
- Current state
- Final output

The frontend communicates with the FastAPI backend using HTTP APIs.

The frontend does not directly communicate with the LLM or modify the supervisor state.

### 3.2 FastAPI Backend

FastAPI is responsible for the application APIs and coordinates the supervisor runtime.

The backend handles:

- Creating supervisors
- Creating orders
- Creating runs
- Starting runs
- Receiving events
- Adding run-specific instructions
- Pausing and resuming runs
- Interrupting and terminating runs
- Returning run history and activities

The backend also acts as the boundary between the LLM and the actual system actions.

The LLM cannot directly modify the database or call external services.

### 3.3 PostgreSQL

PostgreSQL is the persistent source of truth for the supervisor.

The important tables are:

- `supervisors`
- `orders`
- `runs`
- `events`
- `activities`
- `run_instructions`

The `runs` table stores the current lifecycle state of a supervisor run.

It also stores:

- Current state
- Next wake-up time
- Start time
- End time
- Final summary
- Learnings
- Recommendations

This means the supervisor does not depend on process memory to remember where it was.

---

## 4. Long-Running Run Model

Each order gets one supervisor run.

A simplified lifecycle is:

```text
                    ┌─────────┐
                    │ CREATED │
                    └────┬────┘
                         │
                         ▼
                    ┌─────────┐
                    │ RUNNING │
                    └────┬────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        ┌───────────┐         ┌───────────┐
        │ SLEEPING  │         │ COMPLETED │
        └─────┬─────┘         └───────────┘
              │
              │ wake-up
              ▼
        ┌───────────┐
        │ RUNNING   │
        └───────────┘
```

Other lifecycle states:

- `RUNNING → PAUSED`
- `RUNNING → INTERRUPTED`
- `RUNNING → TERMINATED`

The important part is that `SLEEPING` is persisted in the database.

For example:

```text
status       = sleeping
next_wake_at = 2026-09-27 12:30:00
```

The process does not need to remain alive waiting for that time.

---

## 5. Supervisor Runtime

The supervisor runtime is responsible for one execution cycle.

The simplified flow is:

```text
        Wake Run
           │
           ▼
    Check Run Status
           │
           ▼
     Check Max Age
           │
           ▼
     Process Events
           │
           ▼
      Update State
           │
           ▼
   Load Instructions
           │
           ▼
      Call Gemini
           │
           ▼
    Validate Decision
           │
           ▼
    Execute Actions
           │
           ▼
   Record Reasoning
           │
           ▼
   Update Run State
           │
           ▼
       Sleep
```

The runtime does not continuously call Gemini.

After a decision, the runtime stores the requested sleep duration:

```text
next_wake_at = current_time + sleep_minutes
```

and changes the run status to `SLEEPING`.

---

## 6. Event Handling

Events are stored in PostgreSQL before they are processed.

Examples of supported events include:

- `order_created`
- `payment_confirmed`
- `payment_failed`
- `shipment_created`
- `shipment_delayed`
- `delivered`
- `refund_requested`
- `customer_message_received`
- `no_update_for_n_hours`

The event flow is:

```text
Event Simulator
      │
      ▼
POST /api/runs/{run_id}/events
      │
      ▼
Store Event in PostgreSQL
      │
      ▼
Wake Run if required
      │
      ▼
Supervisor Runtime
      │
      ▼
Process Event
      │
      ▼
Update Current State
      │
      ▼
Gemini receives:
  - current state
  - recent events
  - supervisor instruction
  - run instructions
      │
      ▼
Decision
```

For example, when `shipment_delayed` is received, the runtime updates:

```text
shipment_status = delayed
```

The event is also retained in the event history.

---

## 7. State and Memory

The current supervisor state is stored in the `runs.state` JSONB column.

A simplified state can look like:

```json
{
  "order_status": "created",
  "payment_status": "confirmed",
  "shipment_status": "delayed",
  "last_event": "shipment_delayed",
  "last_event_id": "..."
}
```

This state is passed to the LLM together with recent events.

The system therefore has two different types of information:

**Current state**
What is currently true about the order.

**Event history**
What happened during the lifetime of the order.

The LLM receives recent events rather than the complete event history to keep the inference context small.

---

## 8. LLM Responsibility

The LLM is responsible for making a decision about what should happen next.

It receives:

```text
Base supervisor instruction
        +
Run-specific instructions
        +
Current state
        +
Recent events
```

It returns:

```json
{
  "reasoning": "Shipment is delayed and requires investigation.",
  "actions": [
    {
      "action": "message_logistics_team",
      "content": "Please investigate the shipment delay."
    }
  ],
  "sleep_minutes": 15
}
```

The LLM does not own the lifecycle of the run.

In particular, the LLM cannot decide:

- `COMPLETED`

The backend controls terminal states.

This keeps business lifecycle rules outside the model.

---

## 9. Action Execution

The model only recommends actions.

The backend validates the returned action against an allowlist:

- `message_fulfillment_team`
- `message_payments_team`
- `message_logistics_team`
- `message_customer`
- `create_internal_note`

The flow is:

```text
                 Gemini
                   │
                   │ recommended action
                   ▼
          ┌──────────────────┐
          │ Backend          │
          │ validation       │
          └────────┬─────────┘
                   │
            Is action allowed?
              /           \
            No             Yes
            │               │
            ▼               ▼
       Ignore action    Action handler
                            │
                            ▼
                       PostgreSQL
                            │
                            ▼
                       Activity
```

For this assignment, the actions do not call real external services.

Instead, each action creates an activity record in PostgreSQL.

This makes the behavior visible in the UI while keeping the POC small.

---

## 10. Scheduler

The scheduler runs in the FastAPI backend process.

It periodically looks for runs where:

```text
status = sleeping
```

and:

```text
next_wake_at <= current_time
```

A simplified flow is:

```text
             Scheduler
                 │
                 ▼
       Query sleeping runs
                 │
                 ▼
       next_wake_at reached?
             /       \
           No         Yes
           │           │
           │           ▼
           │      Set RUNNING
           │           │
           │           ▼
           │    Supervisor Runtime
           │           │
           └───────────┘
```

The database is used as the source of truth, so a sleeping run can be recovered after a backend restart.

---

## 11. Restart Recovery

One of the reasons for storing `next_wake_at` in PostgreSQL is restart recovery.

For example:

```text
12:00
Run is sleeping
next_wake_at = 12:10

       ↓

Backend crashes

       ↓

Backend restarts at 12:15

       ↓

Scheduler checks PostgreSQL

       ↓

12:10 <= 12:15

       ↓

Run is woken up
```

The run does not lose its state because the important information is persisted in PostgreSQL.

This was preferred over keeping the supervisor state only in application memory.

---

## 12. Run Completion

Run completion is controlled by the backend.

For example, when the `delivered` event is received:

```text
delivered event
      │
      ▼
Update order state
      │
      ▼
Backend detects terminal event
      │
      ▼
Run = COMPLETED
      │
      ▼
Generate final summary
      │
      ▼
Store final output
```

The LLM can recommend actions related to an event, but it cannot decide that the run has completed.

This avoids making a terminal business decision dependent on an LLM response.

The backend can also terminate a run when the maximum allowed run age is exceeded.

---

## 13. Pause, Resume and Termination

Run controls are handled by the backend.

**Pause**

A paused run does not execute the supervisor until it is resumed.

```text
RUNNING / SLEEPING
        │
        ▼
     PAUSED
        │
        ▼
     RESUME
        │
        ▼
     RUNNING
```

**Terminate**

Termination is a terminal state.

```text
RUNNING / SLEEPING / PAUSED
             │
             ▼
        TERMINATED
```

After termination, new supervisor processing is not performed.

**Interrupt**

An interrupted run records the interruption as part of its lifecycle state and does not continue normal processing until explicitly resumed or otherwise handled by the system.

---

## 14. Failure Handling

The supervisor should not crash just because the model is temporarily unavailable.

The agent layer catches model/API errors and returns a safe decision when necessary.

The runtime can then keep the run persisted rather than losing the entire supervisor process.

The action layer also validates model-generated actions before executing them.

For this POC, the external actions are represented as database activity records rather than real integrations.

---

## 15. Why PostgreSQL + Scheduler

For this assignment, I chose a PostgreSQL-backed scheduler instead of introducing a separate workflow system such as Temporal or a message broker.

The main reasons were:

- The application already requires PostgreSQL.
- Supervisor state is naturally persisted there.
- `next_wake_at` is enough for the scheduling requirement.
- The implementation is smaller and easier to understand.
- Restart recovery can be handled from persisted state.
- It keeps the POC focused on the long-running supervisor rather than infrastructure.

For a larger production system with a high number of long-running workflows, I would consider a dedicated workflow engine or queue-based architecture.

---

## 16. Why the LLM Does Not Control Completion

The LLM is probabilistic, while completion is a deterministic business rule.

For example:

```text
LLM:
"Shipment looks complete."

Backend:
"Was the delivered event received?"
```

Only the backend can transition the run to `COMPLETED`.

This separation also makes the system easier to test because terminal states can be verified independently of the model's response.

---

## 17. Current Scope

This implementation intentionally keeps the scope small.

The following are simulated rather than integrated with real external systems:

- Fulfillment messaging
- Payment team messaging
- Logistics messaging
- Customer messaging
- Internal notes

All of these actions are stored as activities and displayed in the UI.

The event simulator is also part of the POC so that the complete lifecycle can be demonstrated without depending on external order systems.

---

## 18. Current Limitations

The current implementation is designed as a take-home POC rather than a production workflow engine.

Some areas that would need additional work for production include:

- Stronger event idempotency guarantees
- More robust concurrency handling around simultaneous events
- Distributed scheduling for multiple backend instances
- Dedicated queue/workflow infrastructure
- Authentication and authorization
- Real integrations with fulfillment, payment, logistics and messaging systems
- More advanced context management for very long-running orders
- Better observability and metrics
- More comprehensive automated tests

These were intentionally kept outside the scope of the current implementation so that the core long-running supervisor flow remains small and demonstrable.