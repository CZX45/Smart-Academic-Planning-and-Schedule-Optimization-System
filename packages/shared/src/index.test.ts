import { describe, expect, it } from 'vitest';
import { HealthResponseSchema } from './index.js';

describe('HealthResponseSchema', () => {
  it('validates API health payloads', () => {
    expect(HealthResponseSchema.parse({ status: 'ok', service: 'api', database_configured: true })).toEqual({
      status: 'ok',
      service: 'api',
      database_configured: true,
    });
  });
});
