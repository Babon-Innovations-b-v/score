// The browser half of viewer_look.py: each place's viewer page opened once in headless Chromium (software WebGL),
// waited on until it says it has loaded the whole copy, then moved to each camera through its #view= link and its
// 3D stage saved as a picture from each. Run through
//   npx -y -p playwright@<pinned> node viewer_look.mjs <jobs.json>
// (npx puts the package's .bin on PATH; the module is found from there). Prints one line a picture.
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import path from "node:path";

const bin = process.env.PATH.split(":").find((part) => part.includes("_npx") && part.endsWith(".bin"));
const { chromium } = createRequire(import.meta.url)(path.join(bin, "..", "playwright"));
const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const LOADED = /triangles\.|Could not open|graphics dropped/;
const SETTLE_MS = 2500;  // frames after the whole copy or a move: the probe and the shadows drawn again
const FRAMES = 10;

// The mean time of up to `most` frames (at most 20 s), in ms.
function frameTime(most) {
  return new Promise((done) => {
    let count = 0;
    const start = performance.now();
    const tick = () => {
      count += 1;
      if (count >= most || performance.now() - start > 20000) done(Math.round((performance.now() - start) / count));
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

// Move to the view in `hash`; resolved two frames after the viewer has moved and probed its light there.
function moveTo(hash) {
  return new Promise((done) => {
    window.addEventListener("hashchange", () => requestAnimationFrame(() => requestAnimationFrame(done)),
                            { once: true });
    location.hash = hash;
  });
}

// ANGLE on GL: Mesa's llvmpipe where no GPU reaches the browser (WSL), several times faster than SwiftShader.
const browser = await chromium.launch({ args: ["--use-angle=gl", "--ignore-gpu-blocklist"] });
for (const job of jobs) {
  const page = await browser.newPage({ viewport: { width: job.width + job.panel, height: job.height } });
  page.setDefaultTimeout(job.timeout_ms);
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  const started = Date.now();
  let said = "", frameMs = null;
  try {
    await page.goto(`${job.url}#${job.shots[0].hash}`);
    await page.waitForFunction((pattern) => new RegExp(pattern).test(document.getElementById("status").textContent),
                               LOADED.source);
    said = await page.textContent("#status");
    await page.waitForTimeout(SETTLE_MS);
    frameMs = await page.evaluate(frameTime, FRAMES);
  } catch (error) {
    said = `timed out: ${await page.textContent("#status").catch(() => "")}`;
  }
  for (const [number, shot] of job.shots.entries()) {
    const shotErrors = [];
    let taken = false;
    try {
      if (number > 0) {
        await page.evaluate(moveTo, shot.hash);
        await page.waitForTimeout(SETTLE_MS);
      }
      // The page's own clip, not an element shot: software WebGL draws a heavy place too slowly for "stable".
      await page.screenshot({ path: shot.out, clip: { x: job.panel, y: 0, width: job.width, height: job.height } });
      taken = true;
    } catch (error) {
      shotErrors.push(`no picture: ${String(error).split("\n")[0]}`);
    }
    console.log(JSON.stringify({ out: shot.out, said, shot: taken, frame_ms: frameMs,
                                 seconds: (Date.now() - started) / 1000, errors: [...errors, ...shotErrors] }));
  }
  await page.close();
}
await browser.close();
