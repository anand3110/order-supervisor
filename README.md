# Order Supervisor

A long-running AI supervisor that monitors a single customer order from creation to completion.

The supervisor reacts to order events, reasons about the current state, performs operational actions, sleeps until the next wake-up, and continues monitoring until the system determines that the run has reached a terminal state.

---

## Architecture

```text
                    ┌──────────────────────┐
                    │      Next.js UI      │
                    │                      │
                    │  Dashboard           │
                    │  Run Details         │
                    │  Event Simulator     │
                    │  Run Controls        │
                    └──────────┬───────────┘
                               │ HTTP
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │                      │
                    │  REST APIs           │
                    │  Run Lifecycle       │
                    │  Event Processing    │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌──────────────────┐       ┌──────────────────┐
        │   PostgreSQL     │       │    Scheduler     │
        │                  │       │                  │
        │  Orders          │       │  Finds sleeping  │
        │  Runs            │       │  runs whose      │
        │  Events          │       │  wake time has   │
        │  Activities      │       │  arrived         │
        │  Instructions    │       └────────┬─────────┘
        │  Run State       │                │
        └──────────────────┘                ▼
                                  ┌──────────────────┐
                                  │ Supervisor       │
                                  │ Runtime          │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │    Gemini LLM    │
                                  │                  │
                                  │  Reasoning       │
                                  │  Actions         │
                                  │  Sleep duration  │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │  Action Services │
                                  │                  │
                                  │  Fulfillment     │
                                  │  Payments        │
                                  │  Logistics       │
                                  │  Customer        │
                                  │  Internal Note   │
                                  └──────────────────┘