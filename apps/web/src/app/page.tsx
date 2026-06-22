"use client";

import {
  ApiRequestError,
  ApiResponseSchemaError,
  fetchHealth,
  type HealthResponse,
} from "@sapsos/shared";
import { useEffect, useState } from "react";

type HealthState =
  | { status: "loading" }
  | { status: "online"; payload: HealthResponse }
  | { status: "offline"; message: string };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

function describeHealthError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected health response shape.";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "Unknown API health error";
}

export default function Home() {
  const [health, setHealth] = useState<HealthState>(() =>
    apiBaseUrl
      ? { status: "loading" }
      : {
          status: "offline",
          message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
        },
  );

  useEffect(() => {
    let cancelled = false;

    if (!apiBaseUrl) {
      return () => {
        cancelled = true;
      };
    }

    fetchHealth(apiBaseUrl, { timeoutMs: 5_000 })
      .then((payload) => {
        if (!cancelled) {
          setHealth({ status: "online", payload });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setHealth({ status: "offline", message: describeHealthError(error) });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const isOk = health.status === "online";
  const healthPayload =
    health.status === "online"
      ? health.payload
      : {
          status: health.status,
          service: "API health",
          database_configured: false,
          message:
            health.status === "offline"
              ? health.message
              : "Checking API health...",
        };

  return (
    <main>
      <section className="card">
        <p className={`badge ${isOk ? "ok" : "warn"}`}>
          {health.status === "loading"
            ? "API checking"
            : isOk
              ? "API connected"
              : "API unavailable"}
        </p>
        <h1>Smart Academic Planning and Schedule Optimization System</h1>
        <p>
          Phase 1 scaffold: Next.js frontend, FastAPI backend, PostgreSQL
          migration baseline, shared API types, and mock-only seed
          infrastructure.
        </p>
        <h2>Backend health</h2>
        <pre>{JSON.stringify(healthPayload, null, 2)}</pre>
        <p className="notice">Mock data — not official university policy.</p>
        <p className="notice">
          Advisor confirmation is required for high-impact academic guidance.
        </p>
      </section>
    </main>
  );
}
