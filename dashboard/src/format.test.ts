import { expect, test } from "vitest";

import { date, label, money, time } from "./format";

test("money shows dollars with cents and thousands", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
  expect(money(61.5)).toBe("$61.50");
});

test("label turns a code into words", () => {
  expect(label("emergency_medical")).toBe("Emergency medical");
  expect(label("premium")).toBe("Premium");
});

test("date shows a calendar date", () => {
  expect(date("2026-06-24")).toBe("Jun 24, 2026");
});

test("time shows the date and time of a timestamp", () => {
  expect(time("2026-11-04T23:30:40+00:00")).toMatch(/^Nov [45], \d{1,2}:30:40/);
});
