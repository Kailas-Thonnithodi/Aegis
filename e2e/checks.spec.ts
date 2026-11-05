import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("checking picked claims scores them against the handlers", async ({
  page,
}) => {
  await page.goto("/#/checks");
  await page.getByLabel("Pick CLM-1001").check();
  await page.getByLabel("Pick CLM-1101").check();
  await expect(page.getByText("2 claims picked")).toBeVisible();
  await page.getByRole("button", { name: "Run checks" }).click();

  await expect(page).toHaveURL(/#\/checks\/\d+$/);
  await expect(page.getByText(/^Finished /)).toBeVisible();
  await expect(
    page.locator("details", { hasText: "CLM-1001" }).locator(".pill"),
  ).toHaveText("Match");
  await expect(
    page.locator("details", { hasText: "CLM-1101" }).locator(".pill"),
  ).toHaveText("Payout miss");
  await expect(
    page.getByLabel("Scores").getByText("1 of 2").first(),
  ).toBeVisible();
});

test("a check run leaves the live queue as it was", async ({ page }) => {
  await page.goto("/");
  const counts = page.getByLabel("Claims by status");
  await expect(counts).toContainText("Waiting");
  const before = await counts.textContent();

  await page.goto("/#/checks");
  await page.getByLabel("Set").selectOption("queue");
  await page.getByRole("button", { name: "Select all shown" }).click();
  await page.getByRole("button", { name: "Run checks" }).click();
  await expect(page.getByText(/^Finished /)).toBeVisible({ timeout: 30_000 });

  await page.goto("/");
  await expect(counts).toHaveText(before ?? "");
});
