import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173/engine/95";
const out = process.argv[3] ?? "snap-modal.png";

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  deviceScaleFactor: 1,
});
const page = await ctx.newPage();
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(300);

const card = page.locator("button:has-text('HPC Outlet Temp')").first();
await card.click();
await page.waitForTimeout(400);

await page.screenshot({ path: out, fullPage: false });
await browser.close();
console.log("wrote", out);
