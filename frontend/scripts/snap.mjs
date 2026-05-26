import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const out = process.argv[3] ?? "snap.png";
const tall = process.argv[4] === "tall";

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1440, height: tall ? 1800 : 900 },
  deviceScaleFactor: 1,
});
const page = await ctx.newPage();
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(400);
await page.screenshot({ path: out, fullPage: false });
await browser.close();
console.log("wrote", out);
