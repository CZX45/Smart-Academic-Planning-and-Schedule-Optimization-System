import { describe, expect, it } from "vitest";

import {
  CreatedLocalStudentProfileResponseSchema,
  createLocalStudentProfile,
  fetchLocalStudentProfiles,
} from "./index.js";

const responsePayload = {
  institution: {
    id: "11111111-1111-4111-8111-111111111111",
    code: "LOCAL-U",
    name: "Student-provided university",
    country: "US",
    timezone: "America/New_York",
    source: {
      source_type: "STUDENT_PROVIDED",
      is_official: false,
      source_reference: "Local onboarding form",
      source_retrieved_at: "2026-08-22T00:00:00Z",
      source_confidence: "student-provided-unverified",
    },
  },
  campus: {
    id: "22222222-2222-4222-8222-222222222222",
    institution_id: "11111111-1111-4111-8111-111111111111",
    code: "MAIN",
    name: "Main campus",
    location: null,
    source: {
      source_type: "STUDENT_PROVIDED",
      is_official: false,
      source_reference: "Local onboarding form",
      source_retrieved_at: "2026-08-22T00:00:00Z",
      source_confidence: "student-provided-unverified",
    },
  },
  student: {
    id: "33333333-3333-4333-8333-333333333333",
    home_institution_id: "11111111-1111-4111-8111-111111111111",
    home_campus_id: "22222222-2222-4222-8222-222222222222",
    expected_graduation_term_id: null,
    external_ref: null,
    display_name: "Local learner",
    class_standing: null,
    programs: [],
    source: {
      source_type: "STUDENT_PROVIDED",
      is_official: false,
      source_reference: "Local onboarding form",
      source_retrieved_at: "2026-08-22T00:00:00Z",
      source_confidence: "student-provided-unverified",
    },
  },
  reason_codes: ["STUDENT_PROVIDED_PROFILE_CREATED"],
  warnings: ["Confirm with an advisor."],
  assumptions: ["School details are unverified."],
  source_references: ["Local onboarding form"],
};

describe("local onboarding client", () => {
  it("lists persisted local profiles through the local-only endpoint", async () => {
    let requestedUrl = "";
    const profiles = await fetchLocalStudentProfiles("http://api.test", {
      fetchFn: async (input) => {
        requestedUrl = String(input);
        return Response.json([responsePayload]);
      },
    });

    expect(requestedUrl).toBe(
      "http://api.test/api/v1/local-onboarding/student-profiles",
    );
    expect(profiles[0]?.student.display_name).toBe("Local learner");
  });

  it("creates an explicitly unverified profile with a typed request", async () => {
    let requestBody: unknown;
    const profile = await createLocalStudentProfile(
      "http://api.test",
      {
        acknowledge_non_official: true,
        display_name: "Local learner",
        institution_code: "LOCAL-U",
        institution_name: "Student-provided university",
        campus_code: "MAIN",
        campus_name: "Main campus",
        country: "US",
        timezone: "America/New_York",
      },
      {
        fetchFn: async (_input, init) => {
          requestBody = JSON.parse(String(init?.body));
          return Response.json(responsePayload, { status: 201 });
        },
      },
    );

    expect(requestBody).toMatchObject({ acknowledge_non_official: true });
    expect(profile.student.id).toBe("33333333-3333-4333-8333-333333333333");
  });

  it("rejects an onboarding payload that claims official source status", () => {
    expect(() =>
      CreatedLocalStudentProfileResponseSchema.parse({
        ...responsePayload,
        student: {
          ...responsePayload.student,
          source: { ...responsePayload.student.source, is_official: true },
        },
      }),
    ).toThrow();
  });
});
