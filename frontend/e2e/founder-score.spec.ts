import { SAMPLE_IDEA, expect, test } from "./fixtures"

const AXES = ["Seen greatness", "Horsepower", "Domain fit", "Sacrifice", "Timing"]

test("founder score: sample founder scorecard, then the founder's own profile", async ({ page, blockedRequests }) => {
  await page.goto("/")
  await page.getByPlaceholder(/Describe your idea/).fill(SAMPLE_IDEA)
  await page.getByRole("button", { name: "Start Mentorship" }).click()
  // Navigate in-app like a founder would; a hard reload can redirect before the store hydrates.
  await page.getByRole("button", { name: "Start Mentor Chat" }).click()
  await page.getByRole("button", { name: "End Chat" }).click()
  await page.getByRole("button", { name: "Build your dashboard" }).click()
  await expect(page).toHaveURL(/\/dashboard/)

  await page.getByRole("button", { name: "Founder score" }).click()
  const panel = page.getByTestId("founder-score-panel")
  await panel.getByTestId("sample-hardware-reviews-founder").click()

  const card = panel.getByTestId("founder-scorecard")
  await expect(card.getByTestId("synthetic-badge")).toHaveText("Fictional sample founder")
  await expect(card.getByTestId("founder-composite")).toContainText("/ 100")
  await expect(card.getByTestId("founder-composite")).toContainText(/Strong|Secondary|Below the bar/)
  for (const axis of AXES.slice(0, 4)) await expect(card.getByTestId("founder-radar")).toContainText(axis)
  await expect(card.getByTestId("founder-timing-stat")).toContainText("Timing (not in the composite)")
  for (const key of ["seen_greatness", "horsepower", "domain_fit", "sacrifice", "timing"]) {
    await expect(card.getByTestId(`signal-${key}`)).toBeVisible()
  }
  await expect(card.getByTestId("signal-timing")).toContainText("not in composite")
  // Evidence traces to the registry entry.
  await expect(card.getByTestId("signal-seen_greatness").getByTestId("signal-evidence")).toContainText("Anduril (tier 1")
  await expect(card.getByTestId("founder-provenance")).toContainText(/Domain tags: (recorded Gemini tags|keyword lexicon)/)
  await expect(card.getByTestId("founder-provenance")).toContainText("as of 2026-03-01")

  // Back, then score a profile typed into the form.
  await panel.getByRole("button", { name: "Back to founders" }).click()
  await panel.getByRole("tab", { name: "Your profile" }).click()
  const form = panel.getByTestId("founder-profile-form")
  await form.getByLabel("Name", { exact: true }).fill("Test Founder")
  await form.getByLabel("Your company's name").fill("Pawsight")
  await form.getByLabel("Role 1 title").fill("Senior Software Engineer")
  await form.getByLabel("Role 1 company").fill("Toast")
  await form.getByLabel("Role 1 start").fill("2016")
  await form.getByLabel("Role 1 end").fill("2021")
  await form.getByRole("button", { name: "Score my profile" }).click()
  const mine = panel.getByTestId("founder-scorecard")
  await expect(mine).toContainText("Test Founder")
  await expect(mine.getByTestId("synthetic-badge")).toHaveCount(0)
  await expect(mine.getByTestId("signal-seen_greatness").getByTestId("signal-evidence")).toContainText("Toast (tier 1")

  expect(blockedRequests).toEqual([])
})
