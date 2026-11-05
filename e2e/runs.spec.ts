import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("running the agent shows its steps, then the decision and payment", async ({
  page,
}) => {
  await page.goto("/#/claims/CLM-1001");
  await page.getByRole("button", { name: "Run agent" }).click();

  await expect(page.getByText("Read the claim")).toBeVisible();
  await expect(page.getByText("Paid $420.00", { exact: true })).toBeVisible();
  await expect(page.locator(".pill")).toHaveText("Decided");
  await expect(page.getByText("Approved", { exact: true })).toBeVisible();
  await expect(page.getByText(/^Paid \$420\.00 on /)).toBeVisible();
});

test("a payout over $1,000 waits for sign-off, then is paid", async ({
  page,
}) => {
  await page.goto("/#/claims/CLM-1002");
  await page.getByRole("button", { name: "Run agent" }).click();

  await expect(page.locator(".pill")).toHaveText("Waiting for sign-off");
  await expect(page.getByText("Payment held for sign-off")).toBeVisible();
  await expect(
    page.getByText("Held for sign-off", { exact: true }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Sign off and pay" }).click();

  await expect(page.getByText(/^Paid \$1,150\.00 on /)).toBeVisible();
  await expect(page.getByText("Signed off")).toBeVisible();
  await expect(page.locator(".pill")).toHaveText("Decided");
});

test("working the queue leaves no claim waiting", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Work the queue" }).click();

  await expect(page.getByRole("button", { name: /^Run agent on/ })).toHaveCount(
    0,
    { timeout: 30_000 },
  );
  await expect(
    page.getByRole("button", { name: "Work the queue" }),
  ).toBeDisabled({
    timeout: 30_000,
  });
});
