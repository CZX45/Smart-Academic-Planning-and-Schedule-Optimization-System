import { expect, test } from "@playwright/test";

test("workflow shell exposes implemented workflows and keyboard hash navigation", async ({
  page,
}) => {
  await page.goto("/");

  const navigation = page.getByRole("navigation", { name: "主要工作流" });
  await expect(navigation).toBeVisible();
  await expect(navigation.getByRole("link")).toHaveCount(10);
  await expect(navigation.getByRole("link", { name: "备份" })).toHaveCount(0);

  const degreeAuditLink = navigation.getByRole("link", { name: "学业审核" });
  await degreeAuditLink.focus();
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/#degree-audit$/);
  await expect(degreeAuditLink).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { name: "学业进度" })).toBeVisible();
});
