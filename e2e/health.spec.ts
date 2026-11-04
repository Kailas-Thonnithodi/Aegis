import { expect, test } from "@playwright/test";

test("the dashboard shows the backend is up", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Aegis Claims" }),
  ).toBeVisible();
  await expect(page.getByText("The backend is up.")).toBeVisible();
});
