import { describe, expect, it } from "vitest";

import {
  formatZhCnBeforeAfterValue,
  getZhCnAdvisoryLabels,
  getZhCnEmptyStateCopy,
  localizeDemoOptionLabel,
  localizeStatusBadge,
  localizeStatusLabel,
} from "./zh-cn";

describe("Simplified Chinese web UI copy helpers", () => {
  it("localizes status and source values without changing the raw enum values", () => {
    expect(localizeStatusLabel("IN_REVIEW")).toBe("审核中");
    expect(localizeStatusLabel("PARSED_WITH_WARNINGS")).toBe("已解析但有警告");
    expect(localizeStatusLabel("BROWSER_EXTENSION")).toBe("浏览器插件导入");
    expect(localizeStatusLabel("Disabled")).toBe("已禁用");
    expect(localizeStatusLabel("CUSTOM_COURSE_SET")).toBe("自选课程集合");
  });

  it("localizes dashboard status badges", () => {
    expect(localizeStatusBadge("COMPLETED_WITH_WARNINGS")).toEqual({
      label: "已完成但有警告",
      tone: "warning",
    });
    expect(localizeStatusBadge(null)).toEqual({
      label: "尚未开始",
      tone: "neutral",
    });
  });

  it("keeps safety boundaries explicit in advisory labels and empty states", () => {
    expect(
      getZhCnAdvisoryLabels([
        "NON_OFFICIAL_IMPORTED_DATA",
        "MANUAL_REVIEW_REQUIRED",
        "ADVISORY_ONLY",
        "VERIFY_IN_OFFICIAL_PORTAL",
      ]),
    ).toEqual([
      { text: "非官方导入数据", tone: "warning" },
      { text: "需要人工审核", tone: "warning" },
      { text: "仅供参考", tone: "info" },
      { text: "请在官方门户人工核对", tone: "danger" },
    ]);

    expect(getZhCnEmptyStateCopy("NO_GENERATED_SCHEDULE_PLANS")).toEqual({
      title: "还没有生成课表方案",
      explanation: "当前还没有生成任何学期课表优化结果。",
      reason: "只有学生手动运行优化后，课表生成器才会显示方案。",
      nextAction: "选择课程集合并生成课表，用于比较仅供参考的课表选项。",
      disclaimer: "仅供参考。不会注册课程，也不会 add/drop/swap/waitlist。",
    });
  });

  it("localizes before-after values for section monitoring", () => {
    expect(formatZhCnBeforeAfterValue(null, "OPEN")).toBe("未知 -> 开放");
    expect(formatZhCnBeforeAfterValue("CLOSED", "")).toBe("已关闭 -> 未知");
  });

  it("localizes demo option labels while preserving unknown data labels", () => {
    expect(
      localizeDemoOptionLabel(
        "candidateCourse",
        "fin-400-registration",
        "FIN 400 HYB · permission and waitlist",
      ),
    ).toBe("FIN 400 HYB · 需要许可且有候补名单");
    expect(
      localizeDemoOptionLabel("candidateProgram", "unknown", "MATH 1044"),
    ).toBe("MATH 1044");
  });
});
