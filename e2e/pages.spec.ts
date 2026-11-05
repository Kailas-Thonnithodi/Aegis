import { expect, test } from "@playwright/test";

test("the queue shows every claim with its status", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.getByText("25 claims")).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(26);
});

test("a claim opens in full with its policy", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Flight home canceled by the airline, rebooked the next morning",
    }),
  ).toBeVisible();
  await expect(page.getByText("Airport hotel, one night")).toBeVisible();
  await expect(
    page.getByText("Meridian Air cancellation notice"),
  ).toBeVisible();
  await expect(page.getByText("Maya Patel", { exact: true })).toBeVisible();
});

test("the instructions are shown read only", async ({ page }) => {
  await page.goto("/#/instructions");
  await expect(page.getByText("# Aegis Agent instructions")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
});
