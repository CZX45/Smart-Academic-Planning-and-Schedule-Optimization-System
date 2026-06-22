import { z } from 'zod';

export const HealthResponseSchema = z.object({
  status: z.literal('ok'),
  service: z.string(),
  database_configured: z.boolean(),
});

export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export async function fetchHealth(apiBaseUrl: string): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return HealthResponseSchema.parse(await response.json());
}
