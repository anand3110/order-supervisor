"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = "http://localhost:8000";

// Your working Order Guardian supervisor
const SUPERVISOR_ID = "ce9ed48f-23b8-4799-808e-3046128c717b";

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
  };
  next_wake_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  final_summary: string | null;
};

type Supervisor = {
  id: string;
  name: string;
  base_instruction: string;
  model: string;
  wake_policy: string;
};

export default function Home() {
  const router = useRouter();

  const [runs, setRuns] = useState<Run[]>([]);
  const [supervisor, setSupervisor] =
    useState<Supervisor | null>(null);

  const [loading, setLoading] = useState(true);

  // Create order form
  const [customerName, setCustomerName] = useState("");
  const [amount, setAmount] = useState("");

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(() => {
      loadDashboard();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  async function loadDashboard() {
    try {
      const [runsResponse, supervisorResponse] =
        await Promise.all([
          fetch(`${API_URL}/api/runs/`),

          fetch(
            `${API_URL}/api/supervisors/${SUPERVISOR_ID}`
          ),
        ]);

      if (!runsResponse.ok || !supervisorResponse.ok) {
        throw new Error("Failed to load dashboard data");
      }

      const runsData = await runsResponse.json();
      const supervisorData =
        await supervisorResponse.json();

      setRuns(runsData);
      setSupervisor(supervisorData);
    } catch (error) {
      console.error(
        "Failed to load dashboard:",
        error
      );
    } finally {
      setLoading(false);
    }
  }

  async function createOrderAndRun() {
    setError("");

    if (!customerName.trim()) {
      setError("Please enter customer name.");
      return;
    }

    const numericAmount = Number(amount);

    if (
      !amount ||
      Number.isNaN(numericAmount) ||
      numericAmount <= 0
    ) {
      setError("Please enter a valid amount.");
      return;
    }

    try {
      setCreating(true);

      // ------------------------------------------------
      // 1. Create the order
      // ------------------------------------------------

      const orderResponse = await fetch(
        `${API_URL}/api/orders/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            customer_name: customerName.trim(),
            amount: numericAmount,
          }),
        }
      );

      if (!orderResponse.ok) {
        const errorData =
          await orderResponse.json().catch(() => null);

        throw new Error(
          errorData?.detail ||
            "Failed to create order."
        );
      }

      const order = await orderResponse.json();

      // ------------------------------------------------
      // 2. Create a supervisor run for the order
      // ------------------------------------------------

      const runResponse = await fetch(
        `${API_URL}/api/runs/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            order_id: order.id,
            supervisor_id: SUPERVISOR_ID,
          }),
        }
      );

      if (!runResponse.ok) {
        const errorData =
          await runResponse.json().catch(() => null);

        throw new Error(
          errorData?.detail ||
            "Failed to create supervisor run."
        );
      }

      const run = await runResponse.json();

      // ------------------------------------------------
      // 3. Start the supervisor
      // ------------------------------------------------

      const startResponse = await fetch(
        `${API_URL}/api/runs/${run.id}/start`,
        {
          method: "POST",
        }
      );

      if (!startResponse.ok) {
        const errorData =
          await startResponse.json().catch(() => null);

        throw new Error(
          errorData?.detail ||
            "Failed to start supervisor run."
        );
      }

      // Clear form
      setCustomerName("");
      setAmount("");

      // Refresh dashboard
      await loadDashboard();

      // Open the new run
      router.push(`/runs/${run.id}`);
    } catch (error) {
      console.error(
        "Failed to create order and run:",
        error
      );

      setError(
        error instanceof Error
          ? error.message
          : "Something went wrong."
      );
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <p className="text-slate-400">
          Loading Order Supervisor...
        </p>
      </main>
    );
  }

  // ------------------------------------------------
  // Run categories
  // ------------------------------------------------

  const activeRuns = runs.filter(
    (run) =>
      run.status === "created" ||
      run.status === "running" ||
      run.status === "sleeping" ||
      run.status === "paused"
  );

  const completedRuns = runs.filter(
    (run) => run.status === "completed"
  );

  const stoppedRuns = runs.filter(
    (run) =>
      run.status === "interrupted" ||
      run.status === "terminated"
  );

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Header */}

        <header className="mb-8">
          <p className="text-sm text-blue-400 font-medium mb-2">
            AI ORDER OPERATIONS
          </p>

          <h1 className="text-3xl font-bold">
            Order Supervisor
          </h1>

          <p className="text-slate-400 mt-2">
            Long-running AI supervision for customer orders
          </p>
        </header>

        {/* Create Order */}

        <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">

          <div className="mb-5">
            <h2 className="text-xl font-semibold">
              Create New Order
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Create an order and immediately start its supervisor run.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* Customer Name */}

            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Customer Name
              </label>

              <input
                type="text"
                value={customerName}
                onChange={(e) =>
                  setCustomerName(e.target.value)
                }
                placeholder="e.g. Rahul Kumar"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Amount */}

            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Order Amount
              </label>

              <input
                type="number"
                min="1"
                value={amount}
                onChange={(e) =>
                  setAmount(e.target.value)
                }
                placeholder="e.g. 2499"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
            </div>

          </div>

          {/* Error */}

          {error && (
            <div className="mt-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          {/* Button */}

          <button
            onClick={createOrderAndRun}
            disabled={creating}
            className="mt-5 w-full md:w-auto px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-sm font-medium transition"
          >
            {creating
              ? "Creating Order..."
              : "Create Order & Start Run →"}
          </button>

        </section>

        {/* Supervisor */}

        {supervisor && (
          <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">

            <div className="flex items-start justify-between">

              <div>
                <p className="text-sm text-slate-400 mb-1">
                  Supervisor Configuration
                </p>

                <h2 className="text-xl font-semibold">
                  {supervisor.name}
                </h2>
              </div>

              <span className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-sm">
                {supervisor.model}
              </span>

            </div>

            <div className="mt-5">

              <p className="text-sm text-slate-400 mb-2">
                Base instruction
              </p>

              <p className="text-slate-300 leading-7">
                {supervisor.base_instruction}
              </p>

            </div>

            <div className="mt-5 flex gap-6 text-sm">

              <div>
                <span className="text-slate-500">
                  Wake policy
                </span>

                <p className="text-slate-300 mt-1">
                  {supervisor.wake_policy}
                </p>
              </div>

              <div>
                <span className="text-slate-500">
                  Total runs
                </span>

                <p className="text-slate-300 mt-1">
                  {runs.length}
                </p>
              </div>

            </div>

          </section>
        )}

        {/* Statistics */}

        <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">

          <StatCard
            title="Total Runs"
            value={runs.length}
          />

          <StatCard
            title="Active"
            value={activeRuns.length}
          />

          <StatCard
            title="Completed"
            value={completedRuns.length}
          />

          <StatCard
            title="Stopped"
            value={stoppedRuns.length}
          />

        </section>

        {/* Active Runs */}

        <section className="mb-8">

          <div className="flex items-center justify-between mb-4">

            <h2 className="text-xl font-semibold">
              Active Supervisor Runs
            </h2>

            <span className="text-sm text-slate-500">
              {activeRuns.length} active
            </span>

          </div>

          {activeRuns.length === 0 ? (
            <EmptyState message="No active supervisor runs." />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

              {activeRuns.map((run) => (
                <RunCard
                  key={run.id}
                  run={run}
                  onView={(runId) =>
                    router.push(`/runs/${runId}`)
                  }
                />
              ))}

            </div>
          )}

        </section>

        {/* Completed Runs */}

        <section className="mb-8">

          <div className="flex items-center justify-between mb-4">

            <h2 className="text-xl font-semibold">
              Completed Supervisor Runs
            </h2>

            <span className="text-sm text-slate-500">
              {completedRuns.length} completed
            </span>

          </div>

          {completedRuns.length === 0 ? (
            <EmptyState message="No completed runs yet." />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

              {completedRuns.map((run) => (
                <RunCard
                  key={run.id}
                  run={run}
                  onView={(runId) =>
                    router.push(`/runs/${runId}`)
                  }
                />
              ))}

            </div>
          )}

        </section>

        {/* Stopped Runs */}

        <section>

          <div className="flex items-center justify-between mb-4">

            <h2 className="text-xl font-semibold">
              Stopped Supervisor Runs
            </h2>

            <span className="text-sm text-slate-500">
              {stoppedRuns.length} stopped
            </span>

          </div>

          {stoppedRuns.length === 0 ? (
            <EmptyState message="No interrupted or terminated runs." />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

              {stoppedRuns.map((run) => (
                <RunCard
                  key={run.id}
                  run={run}
                  onView={(runId) =>
                    router.push(`/runs/${runId}`)
                  }
                />
              ))}

            </div>
          )}

        </section>

      </div>
    </main>
  );
}

function StatCard({
  title,
  value,
}: {
  title: string;
  value: number;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">

      <p className="text-sm text-slate-500">
        {title}
      </p>

      <p className="text-3xl font-bold mt-2">
        {value}
      </p>

    </div>
  );
}

function RunCard({
  run,
  onView,
}: {
  run: Run;
  onView: (runId: string) => void;
}) {
  const statusStyles: Record<string, string> = {
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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">

      {/* Run Header */}

      <div className="flex items-start justify-between gap-4">

        <div>

          <p className="text-lg font-semibold">
            {run.state.customer_name ||
              "Unknown customer"}
          </p>

          <p className="text-xs text-slate-600 mt-1 break-all">
            Run ID: {run.id}
          </p>

        </div>

        <span
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            statusStyles[run.status] ||
            "bg-slate-500/10 text-slate-400"
          }`}
        >
          {run.status.toUpperCase()}
        </span>

      </div>

      {/* State */}

      <div className="grid grid-cols-3 gap-3 mt-5">

        <InfoItem
          label="Order"
          value={
            run.state.order_status || "—"
          }
        />

        <InfoItem
          label="Payment"
          value={
            run.state.payment_status || "—"
          }
        />

        <InfoItem
          label="Shipment"
          value={
            run.state.shipment_status || "—"
          }
        />

      </div>

      {/* View Run */}

      <button
        onClick={() => onView(run.id)}
        className="w-full mt-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium transition"
      >
        View Run →
      </button>

      {/* Final Summary */}

      {run.final_summary && (
        <div className="mt-5 pt-4 border-t border-slate-800">

          <p className="text-xs text-slate-500 mb-1">
            Final summary
          </p>

          <p className="text-sm text-slate-300">
            {run.final_summary}
          </p>

        </div>
      )}

    </div>
  );
}

function InfoItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="bg-slate-950 rounded-lg p-3">

      <p className="text-xs text-slate-500">
        {label}
      </p>

      <p className="text-sm text-slate-300 mt-1 capitalize">
        {value}
      </p>

    </div>
  );
}

function EmptyState({
  message,
}: {
  message: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">

      <p className="text-slate-500">
        {message}
      </p>

    </div>
  );
}