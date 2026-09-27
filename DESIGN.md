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

## 4. Database-Backed Scheduler

The scheduler periodically checks for:

```text
status = sleeping
```

and:

```text
next_wake_at <= current_time
```

When a run is ready, it is moved back to `RUNNING` and the supervisor runtime is executed.

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

## 8. Event-Driven + Scheduled Execution

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

## 9. Handling LLM Failures

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

## 10. Current Scope

The following are simulated:

- Fulfillment communication
- Payment team communication
- Logistics communication
- Customer communication
- Internal notes
- Order events

---
