import { expect, test, type Page } from "@playwright/test";

const first = "11111111-1111-4111-8111-111111111111";
const second = "22222222-2222-4222-8222-222222222222";
const programId = "33333333-3333-4333-8333-333333333333";
const courseId = "44444444-4444-4444-8444-444444444444";
const termId = "55555555-5555-4555-8555-555555555555";
const source = {
  source_type: "IMPORTED",
  is_official: false,
  source_reference: "fixture://synthetic-reviewed",
  source_retrieved_at: "2026-10-18T00:00:00Z",
  source_confidence: "reviewed_import",
};
function profile(id: string) {
  return {
    institution: {
      id: first,
      code: "SYNTHETIC",
      name: "合成测试学校",
      country: "US",
      timezone: "UTC",
      source,
    },
    campus: {
      id: first,
      institution_id: first,
      code: "MAIN",
      name: "合成校区",
      location: null,
      source,
    },
    student: {
      id,
      home_institution_id: first,
      home_campus_id: first,
      expected_graduation_term_id: null,
      external_ref: null,
      display_name: id === first ? "合成学生甲" : "合成学生乙",
      class_standing: null,
      programs: [],
      source: { ...source, source_type: "STUDENT_PROVIDED" },
    },
    reason_codes: [],
    assumptions: [],
    source_references: ["fixture://synthetic-reviewed"],
    warnings: [],
  };
}
function candidates(studentId: string, revision = "one") {
  return {
    student_profile_id: studentId,
    revision,
    programs: [
      {
        id: programId,
        name: "合成已审核专业",
        catalog_year: "2026",
        relationship_type: "PRIMARY_MAJOR",
        reviewed_rule_set_id: programId,
        source,
      },
    ],
    courses: [
      {
        id: courseId,
        code: studentId === first ? "MATH 1044" : "PHYS 1001",
        title: "合成已审核课程",
        credits: "3",
        source,
      },
    ],
    terms: [
      {
        id: termId,
        code: "2027SP",
        starts_on: "2027-01-01",
        ends_on: "2027-05-01",
        source,
      },
    ],
    section_ids: [],
    issues: [],
  };
}
async function setup(page: Page, multiple = false) {
  const posts: Array<{ path: string; body: Record<string, unknown> }> = [];
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === "POST") {
      posts.push({
        path,
        body: route.request().postDataJSON() as Record<string, unknown>,
      });
      await route.fulfill({
        status: 422,
        json: {
          detail: {
            code: "synthetic_validation_failure",
            message: "Synthetic fixture",
          },
        },
      });
    } else if (path === "/health") {
      await route.fulfill({
        json: {
          status: "ok",
          service: "sapsos-api",
          database_configured: true,
        },
      });
    } else if (path.endsWith("/local-onboarding/student-profiles")) {
      await route.fulfill({
        json: multiple ? [profile(first), profile(second)] : [profile(first)],
      });
    } else if (path.endsWith("/academic-workflow")) {
      await route.fulfill({
        json: candidates(path.includes(second) ? second : first),
      });
    } else {
      await route.fulfill({
        status: 404,
        json: { detail: { code: "not_found" } },
      });
    }
  });
  return posts;
}

test("real workflow submits scoped reviewed identities and never writes on navigation", async ({
  page,
}) => {
  const posts = await setup(page);
  await page.goto("/");
  await expect(
    page.getByRole("region", { name: "真实学生学业工作流" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "长期规划", exact: true }).click();
  expect(posts).toHaveLength(0);
  await page
    .getByRole("combobox", { name: "真实学期", exact: true })
    .selectOption(termId);
  await page
    .getByRole("combobox", { name: "已应用课程", exact: true })
    .selectOption(courseId);
  await page.getByRole("button", { name: "计算真实学业审核" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "计算或读取未完成" }),
  ).toBeVisible();
  expect(posts[0].body).toMatchObject({
    student_profile_id: first,
    program_version_id: programId,
    calculation_mode: "CURRENT",
  });
  await page.getByRole("button", { name: "检查真实课程资格" }).click();
  await expect.poll(() => posts.length).toBe(2);
  expect(posts[1].body).toMatchObject({
    student_profile_id: first,
    course_id: courseId,
    target_term_id: termId,
  });
  await page.getByRole("button", { name: "生成真实长期规划" }).click();
  await expect.poll(() => posts.length).toBe(3);
  expect(posts[2].body).toMatchObject({
    student_profile_id: first,
    program_version_id: programId,
    start_term_id: termId,
  });
  await page
    .getByRole("checkbox", { name: "MATH 1044 · 合成已审核课程" })
    .check();
  await page.getByRole("button", { name: "优化真实课表" }).click();
  await expect.poll(() => posts.length).toBe(4);
  expect(posts[3].body).toMatchObject({
    student_profile_id: first,
    term_id: termId,
    section_data_mode: "REVIEWED_IMPORTED",
    candidate_course_ids: [courseId],
  });
});

test("real profile selection survives reload and clears the previous course", async ({
  page,
}) => {
  await setup(page, true);
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "当前档案", exact: true })
    .selectOption(first);
  await expect(
    page.getByRole("combobox", { name: "已应用课程", exact: true }),
  ).toContainText("MATH 1044");
  await page
    .getByRole("combobox", { name: "当前档案", exact: true })
    .selectOption(second);
  await expect(
    page.getByRole("combobox", { name: "已应用课程", exact: true }),
  ).toContainText("PHYS 1001");
  await expect(
    page.getByRole("combobox", { name: "已应用课程", exact: true }),
  ).not.toContainText("MATH 1044");
  await page.reload();
  await expect(
    page.getByRole("combobox", { name: "当前档案", exact: true }),
  ).toHaveValue(second);
  await expect(
    page.getByRole("combobox", { name: "已应用课程", exact: true }),
  ).toContainText("PHYS 1001");
});

test("apply invalidates real candidates and ignores a stale response", async ({
  page,
}) => {
  await setup(page);
  let reads = 0;
  let refreshed = false;
  let staleResponses = 0;
  let release: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/academic-workflow", async (route) => {
    reads += 1;
    const current = reads;
    const stale = !refreshed;
    if (stale) await gate;
    const payload = candidates(first, String(current));
    payload.courses[0].code = stale ? "STALE 1000" : "FRESH 2000";
    await route.fulfill({ json: payload });
    if (stale) staleResponses += 1;
  });
  await page.goto("/");
  await expect.poll(() => reads).toBeGreaterThan(0);
  refreshed = true;
  await page.evaluate(
    (studentId) =>
      window.dispatchEvent(
        new CustomEvent("sapsos-data-applied", { detail: studentId }),
      ),
    first,
  );
  await expect(
    page.getByRole("combobox", { name: "已应用课程", exact: true }),
  ).toContainText("FRESH 2000");
  release?.();
  await expect.poll(() => staleResponses).toBeGreaterThan(0);
  await expect(
    page.getByRole("combobox", { name: "已应用课程", exact: true }),
  ).not.toContainText("STALE 1000");
});
