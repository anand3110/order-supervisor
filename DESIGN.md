# Design Notes

## 1. Goal

The main goal of the project is to build a long-running supervisor for a single order.

The supervisor should be able to:

- React to new order events
- Maintain the current order state
- Decide whether an action is required
- Perform operational actions
- Sleep until it needs to run again
- Continue across multiple events
- Stop when the backend determines that the order has reached a terminal state

The implementation is intentionally kept small because the assignment is a POC.

---

## 2. One Run Per Order

I use one supervisor run for each order.

```text
Order
  │
  └── Supervisor Run
          │
          ├── Events
          ├── Current State
          ├── Activities
          └── Run Instructions
```

---

## 3. Why PostgreSQL Stores the State

The supervisor is long-running, so keeping the state only in application memory would make the system difficult to recover after a restart.

Instead, important information is persisted:

- Run status
- Current state
- Next wake-up time
- Events
- Activities
- Instructions
- Final output

For example:

```text
status = sleeping
next_wake_at = 12:30
```

If the backend restarts before 12:30, the scheduler can read the database and continue the run.

---

## 4. Why a Database-Backed Scheduler

For this POC, I chose a simple PostgreSQL-backed scheduler instead of introducing a separate workflow engine.

The scheduler periodically checks for:

```text
status = sleeping
```

and:

```text
next_wake_at <= current_time
```

When a run is ready, it is moved back to `RUNNING` and the supervisor runtime is executed.

This approach was chosen because:

- PostgreSQL is already required by the application.
- The scheduling state is already stored in the database.
- It keeps the infrastructure small.
- It is easy to understand and demonstrate.
- It provides basic restart recovery.

For a larger production system with many workflows, I would consider a dedicated workflow engine or distributed queue.

---

## 5. LLM Responsibility

The LLM is used for decision making, not for controlling the entire workflow.

The LLM receives:

```text
Supervisor instruction
        +
Run-specific instructions
        +
Current state
        +
Recent events
```

and returns:

- Reasoning
- Actions
- Sleep duration

The backend then validates the response.

This separation is important because the LLM is probabilistic while the workflow state needs deterministic rules.

---

## 6. Why the Backend Owns Completion

The LLM cannot decide that a run is completed.

For example, the backend knows that:

```text
delivered
```

is a terminal order event.

Therefore:

```text
delivered event
      ↓
backend processes event
      ↓
run = COMPLETED
```

The model may reason about the event, but it does not control the terminal transition.

This makes completion predictable and prevents the workflow lifecycle from depending entirely on model output.

---

## 7. Action Validation

The model does not directly execute arbitrary functions.

The backend maintains an allowlist:

- `message_fulfillment_team`
- `message_payments_team`
- `message_logistics_team`
- `message_customer`
- `create_internal_note`

When the model returns an action, the backend checks whether the action exists in this allowlist.

Only valid actions are passed to the corresponding action handler.

```text
LLM
 │
 ▼
Recommended Action
 │
 ▼
Backend Validation
 │
 ├── Invalid → Ignore
 │
 └── Valid
       │
       ▼
   Action Handler
```

This provides a clear boundary between model output and application behavior.

---

## 8. Why Actions Are Simulated

The assignment does not require real integrations with payment, fulfillment, logistics, or messaging systems.

Therefore, the action handlers create activity records in PostgreSQL instead.

For example:

```text
message_logistics_team
        ↓
Activity record
        ↓
Displayed in UI
```

This allows the complete workflow to be demonstrated without requiring external services.

In a production system, these handlers could be replaced with calls to actual internal services.

---

## 9. Event-Driven + Scheduled Execution

The supervisor can be activated in two main ways.

**Event-driven wake-up**

When an event is injected:

```text
New Event
   ↓
Store Event
   ↓
Wake Supervisor
   ↓
Process Event
   ↓
LLM Decision
```

**Scheduled wake-up**

After the supervisor makes a decision:

```text
LLM Decision
   ↓
sleep_minutes
   ↓
next_wake_at
   ↓
Run becomes SLEEPING
   ↓
Scheduler wakes it later
```

Using both mechanisms allows the supervisor to react to external events while still supporting periodic checks.

---

## 10. Handling LLM Failures

The LLM is an external dependency and can temporarily fail.

The agent layer therefore catches API errors and retries the request.

If the model is still unavailable after the retry attempts, the runtime returns a safe decision rather than allowing the entire supervisor process to crash.

The important principle is:

```text
LLM failure
    ↓
Supervisor process should remain alive
    ↓
Run state remains persisted
```

The system can therefore continue operating even when the model provider temporarily has an availability problem.

---

## 11. Current Scope

This project is intentionally implemented as a small POC.

The following are simulated:

- Fulfillment communication
- Payment team communication
- Logistics communication
- Customer communication
- Internal notes
- Order events

The main focus is the supervisor runtime rather than building real integrations.

---

## 12. Tradeoffs

**Simple scheduler vs workflow engine**

A PostgreSQL-backed scheduler is simpler to implement and sufficient for the POC.

A workflow engine would provide stronger workflow guarantees and more advanced execution semantics, but would add infrastructure and complexity.

**Database state vs in-memory state**

Database state adds persistence overhead but provides restart recovery.

For a long-running workflow, persistence is more important than keeping the implementation minimal.

**Single supervisor vs multiple agents**

The system uses one supervisor per order.

Multiple specialized agents could be introduced later, but they would add coordination complexity without being necessary for the current problem.

**Simulated actions vs real integrations**

Simulated actions make the demo deterministic and self-contained.

Real integrations would make the system closer to production but would require additional services, authentication, error handling, and infrastructure.

---

## 13. Production Improvements

If this system were taken beyond the POC, I would consider:

- A dedicated workflow engine or distributed job queue.
- Strong event idempotency using external event IDs.
- Stronger concurrency control for simultaneous events.
- Distributed scheduler workers.
- Authentication and authorization.
- Real integrations with internal services.
- Better observability, metrics, and tracing.
- Automated integration and end-to-end tests.
- More advanced context management for very long-running orders.
- Dead-letter handling for events that repeatedly fail.

These improvements were intentionally kept outside the current scope to keep the take-home implementation small and reliable.