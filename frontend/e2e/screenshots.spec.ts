import path from "node:path"
import { SAMPLE_IDEA, expect, test } from "./fixtures"

// `UPDATE_SCREENSHOTS=1 RESEARCH_FIXTURE_REPLAY_SECONDS=30 make e2e-offline` refreshes the README
// images in docs/screenshots/ (the longer replay leaves time to capture the progress log).
test.skip(!process.env.UPDATE_SCREENSHOTS, "set UPDATE_SCREENSHOTS=1 to regenerate docs screenshots")
const out = (name: string) => path.join(__dirname, "..", "..", "docs", "screenshots", name)

// Wait for fade-ins and transitions to finish; a capture mid-animation looks washed out.
async function settle(page: import("@playwright/test").Page) {
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((a) => a.effect?.getComputedTiming().iterations !== Infinity)
        .map((a) => a.finished.catch(() => undefined)),
    ),
  )
}

async function toDashboard(page: import("@playwright/test").Page) {
  await page.goto("/")
  await page.getByPlaceholder(/Describe your idea/).fill(SAMPLE_IDEA)
  await page.getByRole("button", { name: "Start Mentorship" }).click()
  await page.getByRole("button", { name: "Start Mentor Chat" }).click()
  const chat = page.getByTestId("text-chat-mentor")
  await expect(chat.getByTestId("agent-turn").first()).toBeVisible()
  await chat.getByLabel("Message the sequoia mentor").fill("How did Airbnb get its first hosts to trust a new product?")
  await chat.getByRole("button", { name: "Send message" }).click()
  await expect(chat.getByTestId("agent-turn").nth(1).getByTestId("kb-citations")).toBeVisible()
  return chat
}

test("desktop: research report and knowledge-base guide", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await toDashboard(page)
  await page.getByRole("button", { name: "End Chat" }).click()
  await page.getByRole("button", { name: "Build your dashboard" }).click()
  await page.getByRole("button", { name: "Deep Research Agent" }).click()
  await expect.poll(() => page.getByTestId("research-progress").getByRole("listitem").count()).toBeGreaterThan(3)
  await settle(page)
  await page.screenshot({ path: out("research-progress.png") })
  await expect(page.getByTestId("research-report")).toBeVisible({ timeout: 60_000 })
  await page.getByTestId("research-report").getByRole("heading", { name: "MARKET SPACE ASSESSMENT" }).scrollIntoViewIfNeeded()
  await settle(page)
  await page.screenshot({ path: out("research-report.png") })
  await page.getByRole("button", { name: "Close research panel" }).click()
  await page.getByRole("button", { name: "Learn More" }).first().click()
  await page.getByRole("button", { name: "Generate Guide" }).click()
  await expect(page.getByTestId("kb-sources").first()).toBeVisible()
  await settle(page)
  await page.screenshot({ path: out("kb-guide.png") })
})

test("mobile: mentor text chat", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await toDashboard(page)
  await settle(page)
  await page.screenshot({ path: out("mentor-chat-mobile.png") })
})

for (const [label, width, height] of [["desktop", 1440, 900], ["mobile", 390, 844]] as const) {
  test(`${label}: founder scorecard`, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await toDashboard(page)
    await page.getByRole("button", { name: "End Chat" }).click()
    await page.getByRole("button", { name: "Build your dashboard" }).click()
    await page.getByRole("button", { name: "Founder score" }).click()
    await page.getByTestId("sample-hardware-reviews-founder").click()
    await expect(page.getByTestId("founder-radar")).toBeVisible()
    await settle(page)
    await page.screenshot({ path: out(`founder-score-${label}.png`) })
  })
}
