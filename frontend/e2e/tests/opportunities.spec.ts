import { test, expect } from "../fixtures/auth";

test.describe("Opportunities Page", () => {
  test("page loads with header and description", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/opportunities");

    await expect(page.locator("h1")).toContainText("Opportunities");
    await expect(
      page.getByText("Track and manage government contract opportunities")
    ).toBeVisible();
  });

  test("search input is functional", async ({ authenticatedPage: page }) => {
    await page.goto("/opportunities");

    const searchInput = page.getByPlaceholder("Search opportunities...");
    await expect(searchInput).toBeVisible();
    await searchInput.fill("test query");
    await expect(searchInput).toHaveValue("test query");
  });

  test("action buttons are visible", async ({ authenticatedPage: page }) => {
    await page.goto("/opportunities");

    await expect(
      page.getByRole("button", { name: /Sync SAM\.gov/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Add RFP/i })
    ).toBeVisible();
  });

  test("changes tab runs amendment autopilot impact map", async ({
    authenticatedPage: page,
  }) => {
    const rfpId = 9191;

    await page.route(`**/api/rfps/${rfpId}/snapshots/amendment-impact**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          rfp_id: rfpId,
          from_snapshot_id: 101,
          to_snapshot_id: 102,
          generated_at: "2026-02-14T00:00:00Z",
          amendment_risk_level: "high",
          changed_fields: ["naics_code", "response_deadline"],
          signals: [
            {
              field: "naics_code",
              from_value: "541512",
              to_value: "541519",
              impact_area: "eligibility",
              severity: "high",
              recommended_actions: ["Re-check NAICS alignment."],
            },
          ],
          impacted_sections: [
            {
              proposal_id: 33,
              proposal_title: "DoD Cyber Proposal",
              section_id: 2001,
              section_number: "2.1",
              section_title: "Eligibility and Compliance",
              section_status: "approved",
              impact_score: 84.2,
              impact_level: "high",
              matched_change_fields: ["naics_code"],
              rationale: "NAICS references detected.",
              proposed_patch: "Update section language with amended NAICS.",
              recommended_actions: ["Re-check NAICS alignment."],
              approval_required: true,
            },
          ],
          summary: {
            changed_fields: 2,
            impacted_sections: 1,
            high_impact_sections: 1,
            medium_impact_sections: 0,
            low_impact_sections: 0,
            risk_level: "high",
          },
          approval_workflow: ["1) Review", "2) Patch", "3) Approve"],
        }),
      })
    );

    await page.route(`**/api/rfps/${rfpId}/snapshots/diff**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          from_snapshot_id: 101,
          to_snapshot_id: 102,
          changes: [
            { field: "naics_code", from_value: "541512", to_value: "541519" },
            {
              field: "response_deadline",
              from_value: "2026-03-10",
              to_value: "2026-03-18",
            },
          ],
          summary_from: {},
          summary_to: {},
        }),
      })
    );

    await page.route(new RegExp(`/api/rfps/${rfpId}/snapshots(?:\\?.*)?$`), (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 102,
            notice_id: "NOTICE-102",
            solicitation_number: "E2E-AMEND-9191",
            rfp_id: rfpId,
            user_id: 1,
            fetched_at: "2026-02-14T12:00:00Z",
            posted_date: "2026-02-01T00:00:00Z",
            response_deadline: "2026-03-18T00:00:00Z",
            raw_hash: "hash-102",
            summary: {
              title: "E2E Amendment Opportunity",
              agency: "Department of Defense",
              naics_code: "541519",
              response_deadline: "2026-03-18",
              resource_links_count: 2,
            },
          },
          {
            id: 101,
            notice_id: "NOTICE-101",
            solicitation_number: "E2E-AMEND-9191",
            rfp_id: rfpId,
            user_id: 1,
            fetched_at: "2026-02-13T12:00:00Z",
            posted_date: "2026-02-01T00:00:00Z",
            response_deadline: "2026-03-10T00:00:00Z",
            raw_hash: "hash-101",
            summary: {
              title: "E2E Amendment Opportunity",
              agency: "Department of Defense",
              naics_code: "541512",
              response_deadline: "2026-03-10",
              resource_links_count: 1,
            },
          },
        ]),
      })
    );

    await page.route(`**/api/rfps/${rfpId}`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: rfpId,
          user_id: 1,
          title: "E2E Amendment Opportunity",
          solicitation_number: "E2E-AMEND-9191",
          agency: "Department of Defense",
          rfp_type: "solicitation",
          status: "new",
          posted_date: "2026-02-01T00:00:00Z",
          response_deadline: "2026-03-18T00:00:00Z",
          source_url: null,
          sam_gov_link: null,
          summary: "E2E amendment test.",
          description: "E2E amendment test.",
          is_qualified: true,
          qualification_score: 88,
          estimated_value: 5000000,
          place_of_performance: "Remote",
          created_at: "2026-02-01T00:00:00Z",
          updated_at: "2026-02-14T00:00:00Z",
        }),
      })
    );

    await page.route(`**/api/awards**`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    );
    await page.route(`**/api/contacts**`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    );
    await page.route(`**/api/budget-intel**`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    );

    await page.goto(`/opportunities/${rfpId}`);
    await page.getByRole("button", { name: "Changes" }).click();
    await expect(page.getByText("Snapshot Diff")).toBeVisible({ timeout: 15_000 });
    await page.getByRole("button", { name: "Generate Impact Map" }).click();
    await expect(page.getByText("DoD Cyber Proposal")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Eligibility and Compliance")).toBeVisible({
      timeout: 15_000,
    });
  });
});
