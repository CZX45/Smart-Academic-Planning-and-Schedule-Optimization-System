import { fetchHealth } from '@sapsos/shared';

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export default async function Home() {
  const health = await fetchHealth(apiBaseUrl).catch((error: unknown) => ({
    status: 'unavailable' as const,
    service: 'API unavailable',
    database_configured: false,
    message: error instanceof Error ? error.message : 'Unknown error',
  }));

  const isOk = health.status === 'ok';

  return (
    <main>
      <section className="card">
        <p className={`badge ${isOk ? 'ok' : 'warn'}`}>{isOk ? 'API connected' : 'API unavailable'}</p>
        <h1>Smart Academic Planning and Schedule Optimization System</h1>
        <p>
          Phase 1 scaffold: Next.js frontend, FastAPI backend, PostgreSQL migration baseline, shared API types,
          and mock-only seed infrastructure.
        </p>
        <h2>Backend health</h2>
        <pre>{JSON.stringify(health, null, 2)}</pre>
        <p>
          Mock and seed data are for development only. Students must confirm high-impact academic guidance with the
          school or an advisor.
        </p>
      </section>
    </main>
  );
}
