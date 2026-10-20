// The browser half of pages_test's click test: the Place screen as the server rendered it, opened in headless
// Chromium on a made-up origin whose every request is answered from the job (the page, dash.js, each branch's JSON),
// then a branch opened, an item clicked and its action pressed. Prints one JSON line of what the page did. Run through
//   npx -y -p playwright@<pinned> node screens_click.mjs <job.json>
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import path from "node:path";

const bin = process.env.PATH.split(":").find((part) => part.includes("_npx") && part.endsWith(".bin"));
const { chromium } = createRequire(import.meta.url)(path.join(bin, "..", "playwright"));
const job = JSON.parse(readFileSync(process.argv[2], "utf8"));
const ORIGIN = "http://cockpit.test";
// the 3D view: it shows the message the panel sends it as its title
const VIEW = "<script>addEventListener('message', (event) => { document.title = JSON.stringify(event.data); });</script>";

const browser = await chromium.launch();
const page = await browser.newPage();
const fetched = [], posted = [];
await page.route(`${ORIGIN}/**`, (route) => {
  const request = route.request(), url = new URL(request.url());
  const where = url.pathname + url.search;
  if (where === job.page) return route.fulfill({ contentType: "text/html", body: job.html });
  if (url.pathname === "/static/pages/dash.js") return route.fulfill({ contentType: "text/javascript", path: job.dash });
  if (url.pathname.startsWith("/view/")) return route.fulfill({ contentType: "text/html", body: VIEW });
  if (where in job.branches) {
    fetched.push(where);
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(job.branches[where]) });
  }
  if (request.method() === "POST") {
    posted.push({ url: where, body: request.postDataJSON(), csrf: request.headers()["x-csrftoken"] || "" });
    return route.fulfill({ contentType: "application/json", body: JSON.stringify({ said: "done" }) });
  }
  return route.fulfill({ status: 404, body: "" });
});
await page.context().addCookies([{ name: "csrftoken", value: "token", url: ORIGIN }]);
await page.goto(ORIGIN + job.page);
const before = await page.locator(`[data-title="${job.item}"]`).count();
await page.locator(`details[data-children] > summary:has-text("${job.branch}")`).click();
const item = page.locator(`[data-title="${job.item}"]`);
await item.waitFor();
await item.click();
const panel = page.locator("#panel");
await page.waitForFunction(() => document.querySelector("iframe[data-frames]").contentDocument.title !== "");
const shown = {
  open: await panel.isVisible(), title: await panel.locator("h3").textContent(),
  state: await panel.locator('[data-slot="state"]').textContent(),
  price: await panel.locator('[data-slot="price"]').textContent(),
  button: await panel.locator('[data-slot="post-label"]').textContent(),
  framed: await page.evaluate(() => document.querySelector("iframe[data-frames]").contentDocument.title),
};
await panel.locator('[data-slot="post-label"]').click();
await panel.locator('[data-slot="said"].tone-done:not([hidden])').waitFor({ state: "attached" });  // no stylesheet: a dot has no size
await page.locator(`details[data-children] > summary:has-text("${job.branch}")`).click();
await page.locator(`details[data-children] > summary:has-text("${job.branch}")`).click();
await page.waitForTimeout(300);  // a second load, if the branch asked again
const loads = [...fetched];
// back and forward: the panel is a step of its own; a reload opens the branch and the panel again
await page.goBack();
const back = { open: await panel.isVisible(), hash: await page.evaluate(() => location.hash) };
await page.goForward();
const forward = { open: await panel.isVisible(), title: await panel.locator("h3").textContent() };
await page.reload();
await item.waitFor();
await panel.waitFor();
const reloaded = { open: await panel.isVisible(), title: await panel.locator("h3").textContent(),
                   steps: await page.evaluate(() => history.length) };
console.log(JSON.stringify({ before, fetched: loads, posted, ...shown, back, forward, reloaded }));
await browser.close();
