import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeScenarioSnapshot } from "../test/scenarios";
import { ActivitySurface } from "./ActivitySurface";
import { OverviewSurface } from "./OverviewSurface";

describe("evidence-backed Observe surfaces", () => {
  it("summarizes the v3 workspace without exposing an execution control", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <OverviewSurface
        snapshot={makeScenarioSnapshot()}
        selected={{ kind: "pass", id: "pass-4" }}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
    expect(screen.getByText("Cockpit verification replay")).toBeTruthy();
    expect(screen.getByText("feat/front-end-cockpit-v1")).toBeTruthy();
    expect(screen.getByText("The owner-decision barrier remains open.")).toBeTruthy();
    expect(screen.getByText("cvg review --check")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Current snapshot signals" })).toBeTruthy();
    expect(screen.getByText(/snapshot order unless a signal records/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /copy|execute command/i })).toBeNull();

    const frontier = screen.getByRole("button", {
      name: "Inspect active pass 4 Consensus",
    });
    expect(frontier.getAttribute("aria-pressed")).toBe("true");
    await user.click(frontier);
    expect(onSelect).toHaveBeenCalledWith({ kind: "pass", id: "pass-4" });

    await user.click(screen.getByRole("button", { name: /Task specification/i }));
    expect(onSelect).toHaveBeenCalledWith({
      kind: "artifact",
      id: "artifact_22222222222222222222",
    });

    await user.click(
      screen.getByRole("button", { name: /Pass 4 needs an owner decision/i }),
    );
    expect(onSelect).toHaveBeenCalledWith({
      kind: "issue",
      id: "issue_11111111111111111111",
    });
  });

  it("labels bounded records truthfully and follows only explicit entity references", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <ActivitySurface
        snapshot={makeScenarioSnapshot()}
        selected={null}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByRole("heading", { name: "Activity" })).toBeTruthy();
    expect(
      screen.getByText(/bounded observation, not a durable audit history/i),
    ).toBeTruthy();
    expect(screen.getByText("6 of 6 shown")).toBeTruthy();
    expect(screen.getByText("3/4")).toBeTruthy();
    expect(screen.getByText("timed signals")).toBeTruthy();

    const issues = screen.getByRole("region", { name: "Needs attention" });
    expect(
      within(issues).getByRole("article", {
        name: "Pass 4 needs an owner decision.",
      }),
    ).toBeTruthy();
    expect(within(issues).queryByText(/timestamp unavailable/i)).toBeNull();

    const untimedSignal = screen.getByRole("article", {
      name: "Consensus remains blocked.",
    });
    expect(within(untimedSignal).queryByText(/timestamp unavailable/i)).toBeNull();
    expect(
      screen.getByText(/timestamps unavailable · canonical snapshot order preserved/i),
    ).toBeTruthy();

    const timed = screen.getByRole("region", { name: "Timed observations" });
    expect(
      within(timed)
        .getAllByRole("article")
        .map((article) => article.getAttribute("aria-labelledby")),
    ).toEqual([
      "activity-record-signal-signal-misleading-text",
      "activity-record-signal-signal-newer",
      "activity-record-signal-signal-older",
    ]);

    const retrySignal = screen.getByRole("article", {
      name: "Retry was requested.",
    });
    await user.click(
      within(retrySignal).getByRole("button", {
        name: "Inspect related run run-retry",
      }),
    );
    expect(onSelect).toHaveBeenCalledWith({ kind: "run", id: "run-retry" });

    await user.click(
      screen.getByRole("button", {
        name: "Inspect signal Retry was requested.",
      }),
    );
    expect(onSelect).toHaveBeenCalledWith({
      kind: "signal",
      id: "signal-newer",
    });

    const unlinkedSignal = screen.getByRole("article", {
      name: "Text mentions run-retry but has no entity reference.",
    });
    expect(
      within(unlinkedSignal).getByText("No entity reference recorded"),
    ).toBeTruthy();
    expect(
      within(unlinkedSignal).queryByRole("button", { name: /related/i }),
    ).toBeNull();
  });

  it("filters signals and issues without changing snapshot truth", async () => {
    const user = userEvent.setup();

    render(
      <ActivitySurface
        snapshot={makeScenarioSnapshot()}
        selected={null}
        onSelect={vi.fn()}
      />,
    );

    await user.selectOptions(screen.getByLabelText("Record type"), "issue");
    expect(screen.getByText("2 of 6 shown")).toBeTruthy();
    expect(screen.getByText("Pass 4 needs an owner decision.")).toBeTruthy();
    expect(screen.queryByText("Retry was requested.")).toBeNull();

    await user.selectOptions(screen.getByLabelText("Severity"), "blocking");
    expect(screen.getByText("1 of 6 shown")).toBeTruthy();
    expect(screen.getByText("Pass 4 needs an owner decision.")).toBeTruthy();
    expect(
      screen.queryByText("This prose mentions pass-4 but deliberately has no entity."),
    ).toBeNull();
  });

  it("keeps an empty snapshot explicit", () => {
    const snapshot = makeScenarioSnapshot((candidate) => {
      candidate.signals = [];
      candidate.issues = [];
    });

    render(
      <ActivitySurface
        snapshot={snapshot}
        selected={null}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("No bounded activity observed")).toBeTruthy();
    expect(
      screen.getByText("The current snapshot contains no signals or issues."),
    ).toBeTruthy();
  });
});
