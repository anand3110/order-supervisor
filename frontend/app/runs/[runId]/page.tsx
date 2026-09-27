"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API_URL = "http://localhost:8000";

const EVENT_TYPES = [
  "order_created",
  "payment_confirmed",
  "payment_failed",
  "shipment_created",
  "shipment_delayed",
  "delivered",
  "refund_requested",
  "customer_message_received",
  "no_update_for_n_hours",
];

type Run = {
  id: string;
  order_id: string;
  supervisor_id: string;
  status: string;

  state: {
    customer_name?: string;
    order_status?: string;
    payment_status?: string;
    shipment_status?: string;
    last_event?: string;
    last_supervisor_check?: string;
    last_agent_sleep_minutes?: number;
  };

  next_wake_at: string | null;
  started_at: string | null;
  ended_at: string | null;

  final_summary: string | null;
  learnings: string | null;
  recommendations: string | null;
};

type Activity = {
  id: string;
  activity_type: string;
  action: string | null;
  content: string;
  created_at: string;
};

type Event = {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  processed_at: string | null;
};

type RunInstruction = {
  id: string;
  instruction: string;
  created_at: string;
};

export default function RunDetailsPage() {
  const params = useParams();
  const router = useRouter();

  const runId = params.runId as string;

  const [run, setRun] =
    useState<Run | null>(null);

  const [activities, setActivities] =
    useState<Activity[]>([]);

  const [events, setEvents] =
    useState<Event[]>([]);

  const [instructions, setInstructions] =
    useState<RunInstruction[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [sendingEvent, setSendingEvent] =
    useState(false);

  const [controlLoading, setControlLoading] =
    useState(false);

  const [controlMessage, setControlMessage] =
    useState("");

  const [instructionText, setInstructionText] =
    useState("");

  const [instructionLoading, setInstructionLoading] =
    useState(false);

  const [instructionMessage, setInstructionMessage] =
    useState("");

  const [eventType, setEventType] =
    useState("shipment_delayed");

  const [payload, setPayload] =
    useState(
      JSON.stringify(
        {
          reason: "Carrier delay",
          estimated_delay_hours: 12,
        },
        null,
        2
      )
    );

  const [eventMessage, setEventMessage] =
    useState("");

  useEffect(() => {
    loadRun();

    const interval = setInterval(() => {
      loadRun();
    }, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [runId]);

  async function loadRun() {
    try {
      const [
        runResponse,
        activityResponse,
        eventResponse,
        instructionResponse,
      ] = await Promise.all([
        fetch(
          `${API_URL}/api/runs/${runId}`
        ),

        fetch(
          `${API_URL}/api/runs/${runId}/activities`
        ),

        fetch(
          `${API_URL}/api/runs/${runId}/events`
        ),

        fetch(
          `${API_URL}/api/runs/${runId}/instructions`
        ),
      ]);

      if (!runResponse.ok) {
        throw new Error("Run not found");
      }

      const runData =
        await runResponse.json();

      const activityData =
        await activityResponse.json();

      const eventData =
        await eventResponse.json();

      const instructionData =
        await instructionResponse.json();

      setRun(runData);
      setActivities(activityData);
      setEvents(eventData);
      setInstructions(instructionData);
    } catch (error) {
      console.error(
        "Failed to load run:",
        error
      );
    } finally {
      setLoading(false);
    }
  }

  async function addInstruction() {
    setInstructionMessage("");

    if (!instructionText.trim()) {
      setInstructionMessage(
        "Please enter an instruction."
      );
      return;
    }

    setInstructionLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/runs/${runId}/instructions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            instruction: instructionText.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Failed to add instruction."
        );
      }

      setInstructionText("");

      setInstructionMessage(
        "Instruction added successfully."
      );

      await loadRun();
    } catch (error) {
      console.error(
        "Failed to add instruction:",
        error
      );

      setInstructionMessage(
        error instanceof Error
          ? error.message
          : "Failed to add instruction."
      );
    } finally {
      setInstructionLoading(false);
    }
  }

  async function sendEvent() {
    setEventMessage("");

    let parsedPayload: Record<
      string,
      unknown
    >;

    try {
      parsedPayload =
        JSON.parse(payload);
    } catch {
      setEventMessage(
        "Invalid JSON payload. Please check the format."
      );

      return;
    }

    setSendingEvent(true);

    try {
      const response =
        await fetch(
          `${API_URL}/api/runs/${runId}/events`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              event_type: eventType,
              payload: parsedPayload,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Failed to send event"
        );
      }

      setEventMessage(
        "Event sent successfully. Supervisor is processing it."
      );

      await loadRun();
    } catch (error) {
      console.error(
        "Failed to send event:",
        error
      );

      setEventMessage(
        error instanceof Error
          ? error.message
          : "Failed to send event."
      );
    } finally {
      setSendingEvent(false);
    }
  }

  async function controlRun(action: string) {
    setControlMessage("");

    if (action === "terminate") {
      const confirmed = window.confirm(
        "Are you sure you want to terminate this supervisor run?"
      );

      if (!confirmed) {
        return;
      }
    }

    setControlLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/runs/${runId}/${action}`,
        {
          method: "POST",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            `Failed to ${action} run`
        );
      }

      setControlMessage(
        `Run ${action} request completed successfully.`
      );

      await loadRun();
    } catch (error) {
      console.error(
        `Failed to ${action} run:`,
        error
      );

      setControlMessage(
        error instanceof Error
          ? error.message
          : `Failed to ${action} run.`
      );
    } finally {
      setControlLoading(false);
    }
  }

  function handleEventTypeChange(
    value: string
  ) {
    setEventType(value);

    const payloads: Record<
      string,
      Record<string, unknown>
    > = {
      order_created: {
        source: "event_simulator",
      },

      payment_confirmed: {
        transaction_id:
          "TXN-12345",
      },

      payment_failed: {
        reason:
          "Payment authorization failed",
      },

      shipment_created: {
        tracking_id:
          "TRK-12345",
      },

      shipment_delayed: {
        reason:
          "Carrier delay",
        estimated_delay_hours: 12,
      },

      delivered: {
        delivered_at:
          new Date().toISOString(),
      },

      refund_requested: {
        reason:
          "Customer requested refund",
      },

      customer_message_received: {
        message:
          "Where is my order?",
      },

      no_update_for_n_hours: {
        hours: 24,
      },
    };

    setPayload(
      JSON.stringify(
        payloads[value] || {},
        null,
        2
      )
    );
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <p className="text-slate-400">
          Loading run...
        </p>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <div className="text-center">

          <h1 className="text-2xl font-semibold">
            Run not found
          </h1>

          <button
            onClick={() =>
              router.push("/")
            }
            className="mt-4 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500"
          >
            Back to dashboard
          </button>

        </div>
      </main>
    );
  }

  const terminalRun =
    run.status === "completed" ||
    run.status === "terminated" ||
    run.status === "interrupted";

  return (
    <main className="min-h-screen bg-slate-950 text-white">

      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}

        <div className="flex items-center justify-between mb-8">

          <div>

            <button
              onClick={() =>
                router.push("/")
              }
              className="text-sm text-slate-400 hover:text-white mb-3"
            >
              ← Back to dashboard
            </button>

            <h1 className="text-3xl font-bold">
              Supervisor Run
            </h1>

            <p className="text-slate-400 mt-2">
              {run.state.customer_name ||
                "Unknown customer"}
            </p>

          </div>

          <StatusBadge
            status={run.status}
          />

        </div>

        {/* Run Controls */}

        {!terminalRun && (
          <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">

            <div className="mb-5">

              <h2 className="text-lg font-semibold">
                Run Controls
              </h2>

              <p className="text-sm text-slate-500 mt-1">
                Control the lifecycle of this supervisor run.
              </p>

            </div>

            <div className="flex flex-wrap gap-3">

              {/* Pause */}

              {(run.status === "running" ||
                run.status === "sleeping" ||
                run.status === "created") && (
                <button
                  onClick={() =>
                    controlRun("pause")
                  }
                  disabled={controlLoading}
                  className="px-5 py-2.5 rounded-lg bg-orange-600 hover:bg-orange-500 disabled:bg-slate-700 disabled:text-slate-500 text-sm font-medium transition"
                >
                  {controlLoading
                    ? "Processing..."
                    : "Pause"}
                </button>
              )}

              {/* Resume */}

              {run.status === "paused" && (
                <button
                  onClick={() =>
                    controlRun("resume")
                  }
                  disabled={controlLoading}
                  className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-sm font-medium transition"
                >
                  {controlLoading
                    ? "Processing..."
                    : "Resume"}
                </button>
              )}

              {/* Interrupt */}

              {(run.status === "running" ||
                run.status === "sleeping" ||
                run.status === "paused" ||
                run.status === "created") && (
                <button
                  onClick={() =>
                    controlRun("interrupt")
                  }
                  disabled={controlLoading}
                  className="px-5 py-2.5 rounded-lg bg-yellow-600 hover:bg-yellow-500 disabled:bg-slate-700 disabled:text-slate-500 text-sm font-medium transition"
                >
                  {controlLoading
                    ? "Processing..."
                    : "Interrupt"}
                </button>
              )}

              {/* Terminate */}

              {(run.status === "running" ||
                run.status === "sleeping" ||
                run.status === "paused" ||
                run.status === "created") && (
                <button
                  onClick={() =>
                    controlRun("terminate")
                  }
                  disabled={controlLoading}
                  className="px-5 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:bg-slate-700 disabled:text-slate-500 text-sm font-medium transition"
                >
                  {controlLoading
                    ? "Processing..."
                    : "Terminate"}
                </button>
              )}

            </div>

            {controlMessage && (
              <div className="mt-4 bg-slate-950 border border-slate-800 rounded-lg p-4">
                <p className="text-sm text-slate-300">
                  {controlMessage}
                </p>
              </div>
            )}

          </section>
        )}

        {/* Run-Specific Instructions */}

        {!terminalRun && (
          <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">

            <div className="mb-5">

              <h2 className="text-lg font-semibold">
                Run-Specific Instructions
              </h2>

              <p className="text-sm text-slate-500 mt-1">
                Add instructions that apply only to this supervisor run.
              </p>

            </div>

            <textarea
              value={instructionText}
              onChange={(e) =>
                setInstructionText(
                  e.target.value
                )
              }
              placeholder="e.g. If the shipment is delayed, escalate immediately to the logistics team and keep the customer informed."
              rows={4}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500"
            />

            <button
              onClick={addInstruction}
              disabled={instructionLoading}
              className="mt-4 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-sm font-medium transition"
            >
              {instructionLoading
                ? "Adding..."
                : "Add Instruction"}
            </button>

            {instructionMessage && (
              <div className="mt-4 bg-slate-950 border border-slate-800 rounded-lg p-4">
                <p className="text-sm text-slate-300">
                  {instructionMessage}
                </p>
              </div>
            )}

            {instructions.length > 0 && (
              <div className="mt-6">

                <p className="text-sm text-slate-400 mb-3">
                  Current instructions
                </p>

                <div className="space-y-3">

                  {instructions.map(
                    (instruction) => (
                      <div
                        key={instruction.id}
                        className="bg-slate-950 border border-slate-800 rounded-lg p-4"
                      >
                        <p className="text-sm text-slate-300 leading-6">
                          {instruction.instruction}
                        </p>

                        <p className="text-xs text-slate-600 mt-2">
                          Added{" "}
                          {formatDate(
                            instruction.created_at
                          )}
                        </p>
                      </div>
                    )
                  )}

                </div>

              </div>
            )}

          </section>
        )}

        {/* Current State */}

        <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">

          <InfoCard
            title="Order Status"
            value={
              run.state.order_status ||
              "—"
            }
          />

          <InfoCard
            title="Payment Status"
            value={
              run.state.payment_status ||
              "—"
            }
          />

          <InfoCard
            title="Shipment Status"
            value={
              run.state.shipment_status ||
              "—"
            }
          />

        </section>

        {/* Event Simulator */}

        {!terminalRun && (
          <section className="bg-slate-900 border border-blue-900/50 rounded-xl p-6 mb-8">

            <div className="mb-5">

              <h2 className="text-lg font-semibold">
                Event Simulator
              </h2>

              <p className="text-sm text-slate-500 mt-1">
                Inject an order event and
                wake the supervisor
                immediately.
              </p>

            </div>

            <div className="space-y-5">

              {/* Event Type */}

              <div>

                <label className="text-sm text-slate-400 block mb-2">
                  Event
                </label>

                <select
                  value={eventType}
                  onChange={(e) =>
                    handleEventTypeChange(
                      e.target.value
                    )
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                >

                  {EVENT_TYPES.map(
                    (event) => (
                      <option
                        key={event}
                        value={event}
                      >
                        {formatEventName(
                          event
                        )}
                      </option>
                    )
                  )}

                </select>

              </div>

              {/* Payload */}

              <div>

                <label className="text-sm text-slate-400 block mb-2">
                  Payload
                </label>

                <textarea
                  value={payload}
                  onChange={(e) =>
                    setPayload(
                      e.target.value
                    )
                  }
                  rows={7}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-300 font-mono focus:outline-none focus:border-blue-500"
                />

              </div>

              {/* Send Event */}

              <button
                onClick={sendEvent}
                disabled={sendingEvent}
                className="px-5 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-sm font-medium transition"
              >
                {sendingEvent
                  ? "Processing Event..."
                  : "Send Event"}
              </button>

              {/* Message */}

              {eventMessage && (
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">

                  <p className="text-sm text-slate-300">
                    {eventMessage}
                  </p>

                </div>
              )}

            </div>

          </section>
        )}

        {/* Run Information */}

        <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">

          <h2 className="text-lg font-semibold mb-5">
            Run Information
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

            <Metadata
              label="Run ID"
              value={run.id}
            />

            <Metadata
              label="Order ID"
              value={run.order_id}
            />

            <Metadata
              label="Started"
              value={formatDate(
                run.started_at
              )}
            />

            <Metadata
              label="Ended"
              value={formatDate(
                run.ended_at
              )}
            />

            <Metadata
              label="Last Event"
              value={
                run.state.last_event ||
                "—"
              }
            />

            <Metadata
              label="Last Supervisor Check"
              value={formatDate(
                run.state
                  .last_supervisor_check
              )}
            />

            {run.next_wake_at && (
              <Metadata
                label="Next Wake"
                value={formatDate(
                  run.next_wake_at
                )}
              />
            )}

            {run.state
              .last_agent_sleep_minutes && (
              <Metadata
                label="Agent Sleep"
                value={`${run.state.last_agent_sleep_minutes} minutes`}
              />
            )}

          </div>

        </section>

        {/* Event History */}

        <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">

          <div className="flex items-center justify-between mb-5">

            <h2 className="text-lg font-semibold">
              Event History
            </h2>

            <span className="text-sm text-slate-500">
              {events.length} events
            </span>

          </div>

          {events.length === 0 ? (
            <p className="text-slate-500">
              No events received yet.
            </p>
          ) : (
            <div className="space-y-3">

              {events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-4 p-4 bg-slate-950 rounded-lg"
                >

                  <div className="mt-1 w-2 h-2 rounded-full bg-blue-400" />

                  <div className="flex-1">

                    <div className="flex items-center justify-between gap-4">

                      <p className="font-medium">
                        {formatEventName(
                          event.event_type
                        )}
                      </p>

                      <span className="text-xs text-slate-600">
                        {formatDate(
                          event.created_at
                        )}
                      </span>

                    </div>

                    {Object.keys(
                      event.payload || {}
                    ).length > 0 && (
                      <pre className="text-xs text-slate-500 mt-2 whitespace-pre-wrap">
                        {JSON.stringify(
                          event.payload,
                          null,
                          2
                        )}
                      </pre>
                    )}

                    <p className="text-xs text-green-500 mt-2">
                      {event.processed_at
                        ? "Processed"
                        : "Pending"}
                    </p>

                  </div>

                </div>
              ))}

            </div>
          )}

        </section>

        {/* Agent Activity */}

        <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">

          <div className="flex items-center justify-between mb-5">

            <h2 className="text-lg font-semibold">
              Agent Activity
            </h2>

            <span className="text-sm text-slate-500">
              {activities.length} activities
            </span>

          </div>

          {activities.length === 0 ? (
            <p className="text-slate-500">
              No agent activity yet.
            </p>
          ) : (
            <div className="space-y-4">

              {activities.map(
                (activity) => (
                  <ActivityCard
                    key={activity.id}
                    activity={activity}
                  />
                )
              )}

            </div>
          )}

        </section>

        {/* Final Output */}

        {run.status === "completed" && (
          <section className="bg-slate-900 border border-slate-800 rounded-xl p-6">

            <h2 className="text-lg font-semibold mb-5">
              End of Run
            </h2>

            <div className="space-y-5">

              <OutputBlock
                title="Final Summary"
                content={
                  run.final_summary
                }
              />

              <OutputBlock
                title="Learnings"
                content={
                  run.learnings
                }
              />

              <OutputBlock
                title="Recommendations"
                content={
                  run.recommendations
                }
              />

            </div>

          </section>
        )}

      </div>
    </main>
  );
}

function StatusBadge({
  status,
}: {
  status: string;
}) {
  const styles: Record<
    string,
    string
  > = {
    running:
      "bg-blue-500/10 text-blue-400",

    sleeping:
      "bg-yellow-500/10 text-yellow-400",

    paused:
      "bg-orange-500/10 text-orange-400",

    completed:
      "bg-green-500/10 text-green-400",

    interrupted:
      "bg-red-500/10 text-red-400",

    terminated:
      "bg-red-500/10 text-red-400",

    created:
      "bg-slate-500/10 text-slate-400",
  };

  return (
    <span
      className={`px-4 py-2 rounded-full text-sm font-medium ${
        styles[status] ||
        "bg-slate-500/10 text-slate-400"
      }`}
    >
      {status.toUpperCase()}
    </span>
  );
}

function InfoCard({
  title,
  value,
}: {
  title: string;
  value: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">

      <p className="text-sm text-slate-500">
        {title}
      </p>

      <p className="text-xl font-semibold mt-2 capitalize">
        {value}
      </p>

    </div>
  );
}

function Metadata({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>

      <p className="text-xs text-slate-500">
        {label}
      </p>

      <p className="text-sm text-slate-300 mt-1 break-all">
        {value}
      </p>

    </div>
  );
}

function ActivityCard({
  activity,
}: {
  activity: Activity;
}) {
  const isReasoning =
    activity.activity_type ===
    "agent_reasoning";

  const icon = isReasoning
    ? "🧠"
    : "⚡";

  return (
    <div className="border border-slate-800 rounded-lg p-4">

      <div className="flex items-start gap-3">

        <span className="text-lg">
          {icon}
        </span>

        <div className="flex-1">

          <div className="flex items-center justify-between gap-4">

            <p className="font-medium">
              {isReasoning
                ? "Agent Reasoning"
                : activity.action ||
                  "Activity"}
            </p>

            <span className="text-xs text-slate-600">
              {formatDate(
                activity.created_at
              )}
            </span>

          </div>

          <p className="text-sm text-slate-300 mt-3 leading-6">
            {activity.content}
          </p>

        </div>

      </div>

    </div>
  );
}

function OutputBlock({
  title,
  content,
}: {
  title: string;
  content: string | null;
}) {
  return (
    <div>

      <p className="text-sm font-medium text-slate-400 mb-2">
        {title}
      </p>

      <div className="bg-slate-950 rounded-lg p-4">

        <p className="text-sm text-slate-300 leading-6">
          {content ||
            "No information available."}
        </p>

      </div>

    </div>
  );
}

function formatDate(
  value: string | null | undefined
) {
  if (!value) {
    return "—";
  }

  return new Date(
    value
  ).toLocaleString();
}

function formatEventName(
  eventType: string
) {
  return eventType
    .split("_")
    .map(
      (word) =>
        word.charAt(0).toUpperCase() +
        word.slice(1)
    )
    .join(" ");
}