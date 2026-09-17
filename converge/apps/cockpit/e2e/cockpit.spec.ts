import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

interface LiveEnvelope {
  snapshot: {
    schemaVersion: string;
    snapshotId: string;
    source: string;
    method: {
      activePassId: string | null;
    };
    work: { availability: string };
    execution: { availability: string };
    receipts: { availability: string };
    decomposition: {
      availability: string;
      swimlanes: Array<{ id: string; legIds: string[] }>;
      legs: Array<{ id: string }>;
      edges: Array<{ source: string; target: string }>;
    };
    artifacts: Array<{ label: string; path: string }>;
  };
  transport: {
    stale: boolean;
    servedAt: string;
    error?: { code: string; message: string };
  };
}

async function requireLiveContract(page: Page) {
  await expect
    .poll(async () => {
      const health = await page.request.get("/api/health");
      if (!health.ok()) return [health.status(), "unhealthy"];
      const document = (await health.json()) as Record<string, unknown>;
      return [document.service, document.mode];
    })
    .toEqual(["converge-cockpit", "read-only"]);

  const response = await page.request.get("/api/snapshot");
  expect(response.ok()).toBe(true);
  const envelope = (await response.json()) as LiveEnvelope;
  expect(envelope.snapshot.schemaVersion).toBe("3.0");
  expect(envelope.snapshot.snapshotId).toMatch(/^ws3_[0-9a-f]{32}$/);
  expect(envelope.snapshot.source).toBe("workspace");
  expect(envelope.transport.stale).toBe(false);
  return envelope;
}

async function openPrimaryView(page: Page, label: string) {
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Playwright viewport is required");
  const backdrop = page.locator(".drawer-backdrop--visible");
  if (viewport.width < 1280 && (await backdrop.count()) > 0) {
    await page
      .locator('#cockpit-inspector button[aria-label="Collapse inspector"]')
      .click();
    await expect(backdrop).toBeHidden();
  }

  if (viewport.width < 768) {
    const mobileLabel =
      label === "Decompose" ? "Lanes" : label === "Proof" ? "Docs" : label;
    await page
      .locator(".mobile-nav button")
      .filter({
        has: page.locator("span", {
          hasText: new RegExp(`^${mobileLabel}$`),
        }),
      })
      .click();
    return;
  }

  const navigation = page.locator("#cockpit-navigation");
  if (viewport.width <= 1023) {
    const toggle = page.locator(".command-bar__panel-toggle--left");
    if ((await toggle.getAttribute("aria-expanded")) !== "true") {
      await toggle.click();
    }
  }
  await navigation
    .locator(".nav-item")
    .filter({
      has: page.locator(".nav-item__copy strong", {
        hasText: new RegExp(`^${label}$`),
      }),
    })
    .click();
}

async function expectWorkspaceState(page: Page, label: string) {
  await expect(
    page.locator(".workspace-pulse > summary"),
  ).toHaveAttribute("aria-label", new RegExp(label));
}

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("renders only a live WorkspaceSnapshot 3.0 and keeps observation requests read-only", async ({ page }) => {
  const methods: Array<{ method: string; url: string }> = [];
  page.on("request", (request) => {
    methods.push({ method: request.method(), url: request.url() });
  });
  const envelope = await requireLiveContract(page);

  await page.goto("/");
  await expectWorkspaceState(page, "Live workspace");
  await expect(page.getByText("Replay fixture")).toHaveCount(0);
  await expect(page.getByText("Live workspace unavailable")).toHaveCount(0);
  await expect(page.getByRole("main")).toHaveClass(/cockpit-shell/);
  await expect(page.getByText(envelope.snapshot.snapshotId.slice(0, 12))).toHaveCount(
    0,
  );

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.locator(".command-dock")).toHaveCount(0);
  await expect(page.getByText("CLI execution required")).toHaveCount(0);

  expect(methods.length).toBeGreaterThan(0);
  expect(
    methods.filter(({ method }) => method !== "GET"),
    `non-GET browser requests: ${JSON.stringify(methods)}`,
  ).toEqual([]);
});

test("navigates every empty lifecycle view without inventing data", async ({
  page,
}) => {
  const envelope = await requireLiveContract(page);
  expect(envelope.snapshot.work.availability).toBe("empty");
  expect(envelope.snapshot.execution.availability).toBe("empty");
  expect(envelope.snapshot.receipts.availability).toBe("empty");

  await page.goto("/");
  await expectWorkspaceState(page, "Live workspace");

  await openPrimaryView(page, "Work");
  await expect(page.getByRole("heading", { name: "Work" })).toBeVisible();
  await expect(page.getByText("No work has been decomposed")).toBeVisible();

  await openPrimaryView(page, "Runs");
  await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();
  await expect(page.getByText("No execution records observed")).toBeVisible();

  await openPrimaryView(page, "Docs");
  await expect(
    page.getByRole("heading", { name: "Documents & proof" }),
  ).toBeVisible();
  await page.locator(".document-receipts summary").click();
  await expect(page.getByText("No settlements have emitted receipts.")).toBeVisible();

  await openPrimaryView(page, "Artifacts");
  await expect(page.getByRole("heading", { name: "Artifacts" })).toBeVisible();
  await expect(page.getByRole("tablist", { name: "Choose a Converge pass" })).toBeVisible();

  await openPrimaryView(page, "Health");
  await expect(page.getByRole("heading", { name: "Health" })).toBeVisible();

  await openPrimaryView(page, "Journey");
  await expect(
    page.getByRole("region", { name: "Method journey", exact: true }),
  ).toBeVisible();
});

test("shows canonical seams and legs in graph and readable projections", async ({
  page,
}) => {
  const envelope = await requireLiveContract(page);
  expect(envelope.snapshot.decomposition.availability).toBe("available");
  expect(envelope.snapshot.decomposition.swimlanes).toHaveLength(1);
  expect(envelope.snapshot.decomposition.legs).toHaveLength(2);
  expect(
    envelope.snapshot.decomposition.edges.map(({ source, target }) => ({
      source,
      target,
    })),
  ).toEqual([
    {
      source: "swimlane-checkout-leg-01",
      target: "swimlane-checkout-leg-02",
    },
  ]);

  await page.goto("/");
  await openPrimaryView(page, "Decompose");
  const decompose = page.locator(".surface--decompose");
  await expect(
    decompose.getByRole("heading", { name: "Decompose" }),
  ).toBeVisible();
  await expect(decompose.getByText("Why this seam")).toBeVisible();
  await expect(decompose.locator(".decomposition-plan__legs").getByRole("button", { name: /Validate the cart/i })).toBeVisible();
  await expect(decompose.locator(".decomposition-plan__legs").getByRole("button", { name: /Charge and write the order/i })).toBeVisible();
  await expect(decompose.getByText("cart.*", { exact: true })).toBeVisible();
  await expect(decompose.getByText("order.*", { exact: true })).toBeVisible();

  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Playwright viewport is required");
  if (viewport.width >= 768) {
    await page
      .getByLabel("Decomposition presentation")
      .getByRole("button", { name: "Map", exact: true })
      .click();
    const graph = page.getByRole("application", {
      name: "Swimlane decomposition graph",
    });
    await expect(graph).toBeVisible();
    const firstLeg = graph.getByRole("button", {
      name: /Validate the cart, proposed/i,
    });
    await firstLeg.focus();
    await page.keyboard.press("Enter");
    await expect(firstLeg).toHaveAttribute("aria-pressed", "true");
    const secondLeg = graph.getByRole("button", {
      name: /Charge and write the order, proposed/i,
    });
    await secondLeg.focus();
    await page.keyboard.press("Space");
    await expect(secondLeg).toHaveAttribute("aria-pressed", "true");
    const collapseInspector = page
      .getByRole("complementary", { name: "Selection inspector" })
      .getByRole("button", { name: "Collapse inspector" });
    if (await collapseInspector.isVisible()) {
      await collapseInspector.click();
    }
    await page
      .getByLabel("Decomposition presentation")
      .getByRole("button", { name: "Read", exact: true })
      .click();
  }

  await expect(decompose.getByText("Validate the cart").first()).toBeVisible();
});

test("opens hash-bound Markdown as a readable document", async ({ page }) => {
  const envelope = await requireLiveContract(page);
  expect(
    envelope.snapshot.artifacts.some(
      (artifact) =>
        artifact.label === "Project README" && artifact.path === "README.md",
    ),
  ).toBe(true);

  await page.goto("/");
  await openPrimaryView(page, "Docs");
  await expect(
    page.getByRole("heading", { name: "Documents & proof" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Project README/ }).click();
  const inlineReader = page.locator(".document-browser__reader");
  await expect(
    inlineReader.getByRole("heading", { name: "Checkout proving workspace" }),
  ).toBeVisible();
  await expect(inlineReader.getByRole("cell", { name: "Decompose" })).toBeVisible();
  await expect(inlineReader.getByText("cart.* -> validate -> charge -> order.*")).toBeVisible();
  await inlineReader.getByRole("button", { name: /Full screen/ }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("heading", { name: "Checkout proving workspace" }),
  ).toBeVisible();
  await expect(dialog.getByRole("cell", { name: "Decompose" })).toBeVisible();
  await expect(dialog.getByText("cart.* -> validate -> charge -> order.*")).toBeVisible();
  await dialog.getByRole("button", { name: "Close artifact viewer" }).click();
  await expect(dialog).toBeHidden();
});

test("exposes branded Codex and Claude Agent ACP choices", async ({ page }) => {
  await requireLiveContract(page);
  await page.goto("/");
  await openPrimaryView(page, "Ask");

  await expect(page.getByRole("heading", { name: "Ask", exact: true })).toBeVisible();
  await expect(page.locator(".command-bar__panel-toggle--right")).toBeHidden();
  await expect(page.locator(".inspector")).toBeHidden();
  await expect(
    page.getByRole("textbox", { name: "Question for the selected ACP agent" }),
  ).toBeVisible();
  await expect(page.getByText(/Read-only ACP\. Converge/)).toBeVisible();

  // Engine and model live behind a composer popover, so the choices are only
  // reachable once it is open.
  await page.getByRole("button", { name: /^Engine and model:/ }).click();
  const agentGroup = page.getByRole("group", { name: "Choose ACP agent" });
  await expect(agentGroup).toBeVisible();
  const codexButton = agentGroup.getByRole("button", { name: /^Codex,/i });
  const claudeButton = agentGroup.getByRole("button", { name: /^Claude Agent,/i });
  await expect(codexButton).toBeVisible();
  await expect(claudeButton).toBeVisible();
  await expect(page.getByRole("button", { name: /ChatGPT/i })).toHaveCount(0);

  // The marks are inline so they inherit the interface colour; they still have to
  // be drawn at a legible size rather than collapsing to an empty box.
  for (const provider of ["codex", "claude"]) {
    const mark = agentGroup.locator(`.ask-agent-mark--${provider}`);
    await expect(mark).toBeVisible();
    await expect(mark.locator("svg")).toBeVisible();
    const box = await mark.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(20);
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(20);
  }

  // Codex is blocked by the safe-access policy: it stays focusable so the reason
  // is reachable, announces itself as disabled, and cannot become the engine.
  await expect(claudeButton).toHaveAttribute("aria-pressed", "true");
  await expect(codexButton).toHaveAttribute("aria-disabled", "true");
  await expect(codexButton).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByText(/cannot suppress local read and search tools/i)).toBeVisible();

  await codexButton.focus();
  await expect(codexButton).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(codexButton).toHaveAttribute("aria-pressed", "false");
  await expect(claudeButton).toHaveAttribute("aria-pressed", "true");
});

test("Ask sends project scope by default and New chat clears carried history", async ({ page }) => {
  await requireLiveContract(page);
  const snapshotResponse = await page.request.get("/api/snapshot");
  expect(snapshotResponse.ok()).toBe(true);
  const envelope = await snapshotResponse.json();
  const snapshot = envelope.snapshot;
  const requests: Array<Record<string, unknown>> = [];
  await page.route("**/api/ask", async (route) => {
    const request = route.request().postDataJSON() as Record<string, unknown>;
    requests.push(request);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        turnId: `turn_e2e_${requests.length}`,
        agentId: request.agentId,
        snapshotId: snapshot.snapshotId,
        grounding: {
          snapshotId: snapshot.snapshotId,
          observedAt: snapshot.observedAt,
          methodology: {
            tool: "cvg",
            version: snapshot.method.version,
            digest: "f".repeat(64),
          },
          entity: null,
          artifacts: [],
        },
        answer: `Grounded answer ${requests.length}`,
        steps: [],
        activity: [],
        stopReason: "end_turn",
        elapsedMs: 12,
      }),
    });
  });

  await page.goto("/");
  await openPrimaryView(page, "Ask");
  const textbox = page.getByRole("textbox", {
    name: "Question for the selected ACP agent",
  });
  await textbox.fill("Explain the project frontier.");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Grounded answer 1")).toBeVisible();
  expect(requests[0].context).toEqual({ entity: null, artifactIds: [] });

  await page.getByRole("button", { name: "Start new chat" }).click();
  await expect(page.getByRole("heading", { name: /What should we explore in/ })).toBeVisible();
  await expect(textbox).toBeFocused();
  await textbox.fill("What should happen next?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Grounded answer 2")).toBeVisible();
  expect(requests[1].history).toEqual([]);
});

test("opens a pass blade and exposes bounded Overview and Activity views", async ({ page }) => {
  await requireLiveContract(page);
  await page.goto("/");

  await openPrimaryView(page, "Journey");
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Playwright viewport is required");
  const captureButton =
    viewport.width < 768
      ? page
          .locator(".mobile-pass-list")
          .getByRole("button", { name: /\bCapture\b/i })
      : page
          .getByRole("application", { name: "Converge method journey" })
          .getByRole("button", { name: /^Capture,/i });
  await captureButton.click();
  const blade = page.getByRole("complementary", { name: /Capture pass blade/i });
  await expect(blade).toBeVisible();
  await expect(blade.getByRole("heading", { name: "Capture" })).toBeVisible();
  await expect(blade.getByRole("tab", { name: "Overview" })).toBeVisible();
  await expect(blade.getByRole("tab", { name: "Evidence" })).toBeVisible();
  await expect(blade.getByRole("tab", { name: "Activity" })).toBeVisible();

  await openPrimaryView(page, "Overview");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Method map" })).toBeVisible();
  const panelGeometry = await page.locator(".overview-pulse, .overview-method-map, .overview-delivery, .overview-attention, .overview-work-proof, .overview-activity").evaluateAll((panels) =>
    panels.map((panel) => ({
      clientHeight: panel.clientHeight,
      scrollHeight: panel.scrollHeight,
    })),
  );
  expect(panelGeometry).toHaveLength(6);
  expect(
    panelGeometry.every(
      ({ clientHeight, scrollHeight }) => scrollHeight <= clientHeight + 1,
    ),
  ).toBe(true);
  const overviewGrid = page.locator(".overview-control-center");
  const gridGeometry = await overviewGrid.evaluate((grid) => ({
    clientHeight: grid.clientHeight,
    scrollHeight: grid.scrollHeight,
  }));
  expect(gridGeometry.scrollHeight).toBeGreaterThan(gridGeometry.clientHeight);
  await page.locator(".overview-activity").scrollIntoViewIfNeeded();
  await expect(page.getByRole("heading", { name: "Current snapshot signals" })).toBeVisible();

  await openPrimaryView(page, "Activity");
  await expect(page.getByRole("heading", { name: "Activity" })).toBeVisible();
  await expect(page.getByText(/bounded observation, not a durable audit history/i)).toBeVisible();
  await expect(page.getByText("Record type", { exact: true })).toBeVisible();
  await expect(page.getByText("Severity", { exact: true })).toBeVisible();
  const activityGeometry = await page.locator(".activity-record").evaluateAll((records) =>
    records.map((record) => ({
      clientWidth: record.clientWidth,
      scrollWidth: record.scrollWidth,
    })),
  );
  expect(
    activityGeometry.every(
      ({ clientWidth, scrollWidth }) => scrollWidth <= clientWidth + 1,
    ),
  ).toBe(true);
});

test("fits its viewport and switches to semantic navigation on mobile", async ({
  page,
}) => {
  await requireLiveContract(page);
  await page.goto("/");
  await expectWorkspaceState(page, "Live workspace");

  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Playwright viewport is required");
  const geometry = await page.evaluate(() => ({
    viewportWidth: document.documentElement.clientWidth,
    documentWidth: document.documentElement.scrollWidth,
    viewportHeight: window.innerHeight,
    documentHeight: document.documentElement.scrollHeight,
    bodyHeight: document.body.scrollHeight,
  }));
  expect(geometry.documentWidth).toBeLessThanOrEqual(
    geometry.viewportWidth + 1,
  );
  if (viewport.width >= 768) {
    expect(geometry.documentHeight).toBeLessThanOrEqual(
      geometry.viewportHeight + 1,
    );
    expect(geometry.bodyHeight).toBeLessThanOrEqual(geometry.viewportHeight + 1);
  }

  if (viewport.width < 768) {
    await expect(page.locator(".mobile-nav")).toBeVisible();
    await openPrimaryView(page, "Journey");
    await expect(page.locator(".mobile-pass-list")).toBeVisible();
    await expect(page.locator(".lineage-surface__desktop")).toBeHidden();
  } else {
    await expect(page.locator(".mobile-nav")).toBeHidden();
    await openPrimaryView(page, "Journey");
    await expect(page.locator(".lineage-surface__desktop")).toBeVisible();
  }
});

test("passes WCAG A/AA automated checks and exposes a visible stale state", async ({
  page,
}) => {
  const live = await requireLiveContract(page);
  await page.route("**/api/events", (route) => route.abort("failed"));
  await page.route("**/api/snapshot", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...live,
        transport: {
          stale: true,
          servedAt: new Date().toISOString(),
          error: {
            code: "SNAPSHOT_REFRESH_FAILED",
            message: "The CLI snapshot could not be refreshed.",
          },
        },
      }),
    });
  });

  await page.goto("/");
  await expectWorkspaceState(page, "Last-good snapshot");
  await expect(
    page.getByText("The CLI snapshot could not be refreshed."),
  ).toBeVisible();

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    results.violations,
    results.violations
      .map(
        (violation) =>
          `${violation.id}: ${violation.help} (${violation.nodes.length} nodes)`,
      )
      .join("\n"),
  ).toEqual([]);
});
