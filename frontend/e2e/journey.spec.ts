import { SAMPLE_IDEA, expect, test } from "./fixtures"

test("idea to research report, KB-cited guide, and mentor chat with recalled memory", async ({ page, request, blockedRequests }) => {
  // Each run gets a fresh SQLite memory file (playwright.config.ts), so nothing is pre-seeded.
  const before = await (await request.get("http://127.0.0.1:8001/memories")).json()
  expect(before.memories).toEqual([])

  // 1. Submit an idea
  await page.goto("/")
  await expect(page.getByTestId("offline-banner")).toContainText("research replays recorded Gemini runs")
  await page.getByPlaceholder(/Describe your idea/).fill(SAMPLE_IDEA)
  await page.getByRole("button", { name: "Start Mentorship" }).click()
  await expect(page).toHaveURL(/\/mentorship/)

  // Mentor chat (offline text transport): the founder states pricing, which goes to memory.
  await page.getByRole("button", { name: "Start Mentor Chat" }).click()
  const mentor = page.getByTestId("text-chat-mentor")
  await expect(mentor.getByTestId("agent-turn").first()).toContainText("Interesting space")
  await mentor.getByLabel("Message the sequoia mentor").fill(
    "We plan to charge each clinic $300 a month, and our first customers are independent vet clinics in Ohio."
  )
  await mentor.getByRole("button", { name: "Send message" }).click()
  const firstAnswer = mentor.getByTestId("agent-turn").nth(1)
  await expect(firstAnswer.getByTestId("kb-citations")).toBeVisible()
  const stored = await (await request.get("http://127.0.0.1:8001/memories")).json()
  expect(stored.memories.map((m: { memory: string }) => m.memory)).toEqual([
    "We plan to charge each clinic $300 a month, and our first customers are independent vet clinics in Ohio.",
  ])
  await page.getByRole("button", { name: "End Chat" }).click()
  await page.getByRole("button", { name: "Build your dashboard" }).click()
  await expect(page).toHaveURL(/\/dashboard/)

  // 2. Research progresses through the task/status flow to a rendered report
  await page.getByRole("button", { name: "Deep Research Agent" }).click()
  const panel = page.getByTestId("research-panel")
  const progress = panel.getByTestId("research-progress")
  await expect(progress).toBeVisible()
  await expect(progress.getByRole("list", { name: "Research log" }).getByRole("listitem").first()).toBeVisible()
  const report = panel.getByTestId("research-report")
  await expect(report).toBeVisible({ timeout: 60_000 })
  await expect(progress).toBeHidden()
  await expect(report.getByRole("heading", { name: "MARKET SPACE ASSESSMENT" })).toBeVisible()
  // The idea was submitted verbatim with no dashboard answers, so the prompt hash matches.
  await expect(report).toContainText("Offline mode: replaying the exact deep-research recording for this prompt")
  await expect(report.locator(".cite-chip").first()).toBeVisible()
  await panel.getByRole("button", { name: "Close research panel" }).click()

  // 3. Resource drawer: guide grounded in retrieved Sequoia passages, with numbered citations
  await page.getByRole("button", { name: "Learn More" }).first().click()
  await page.getByRole("button", { name: "Generate Guide" }).click()
  const sources = page.getByTestId("kb-sources").first()
  await expect(sources).toBeVisible()
  expect(await sources.getByRole("listitem").count()).toBeGreaterThanOrEqual(2)
  await expect(sources).toContainText(/Podcast transcript|sequoiacap\.com/)
  await expect(page.getByTestId("kb-guide").locator(".cite-chip").first()).toBeVisible()
  await page.keyboard.press("Escape")
  await page.mouse.click(10, 400) // backdrop closes the drawer
  await expect(sources).toBeHidden()

  // 4. Floating mentor: answers with a KB citation and recalls the stored pricing memory
  await page.getByRole("button", { name: "Chat with mentor" }).click()
  const quick = page.getByTestId("mentor-chat-panel")
  await expect(quick.getByTestId("agent-turn").first()).toBeVisible()
  await quick.getByLabel("Message the sequoia mentor").fill("What did I tell you earlier about pricing?")
  await quick.getByRole("button", { name: "Send message" }).click()
  const recall = quick.getByTestId("agent-turn").nth(1)
  await expect(recall.getByTestId("recalled-memories")).toContainText("$300 a month")
  await expect(recall).toContainText("you told me")
  await expect(recall.getByTestId("kb-citations")).toBeVisible()

  expect(blockedRequests, "the browser tried to reach external hosts").toEqual([])
})
