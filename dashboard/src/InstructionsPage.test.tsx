import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { InstructionsPage } from "./InstructionsPage";
import { mockApi } from "./testing";

test("shows the instructions read only", async () => {
  mockApi({ "GET /api/instructions": { text: "# Aegis Agent instructions" } });
  render(<InstructionsPage />);

  expect(await screen.findByText("# Aegis Agent instructions")).toBeTruthy();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});
