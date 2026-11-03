# Video script: one recording, two parts

Voiceover script with on-screen actions. Read **Say** aloud, do **Screen** while you say it.
About 150 words per minute. Each part is written for roughly 4 minutes, leaving slack under a 5-minute budget.

**Before recording**

- X and Y are filled in (bias 1,852 MW, P90 buffer 4,306 MW, all-January basis). Re-check them if you re-ingest.
- Run `make up` (or `make api` and `make web`). Open the portal at `localhost:3000` (or `:5173`) and `slides.html` in a second window.
- Set the portal to delivery day 2026-01-15, cutoff 09:00, P90, "Errors known at the cutoff". Reload once so it is warm.
- Close other tabs and notifications. Zoom the browser to about 125% so text is readable.
- Record the screen and the voice as separate takes if you can. It is easier to re-do a sentence.

---

## Recorded voiceover (2026_11_02_15_57_33.mp3, 4:43)

The screen recording (`make demo-video`) is timed to this audio. Times are when each section is first spoken, from a transcript of the mp3.

| Time | Section | On screen |
| --- | --- | --- |
| 0:00 | 1.1 The finding | Slide 1 |
| 0:37 | 1.2 Portal overview | Portal header and controls |
| 0:58 | 1.3 One day | Chart, then the publish-time line |
| 1:29 | 1.4 Accuracy and buffer | Accuracy card, then buffer card |
| 2:09 | 1.5 Toggle controls | P95, then retrospective, then back |
| 2:22 | 1.6 How far to trust it | Coverage note, then slide 1 |
| 2:53 | 2.1 Architecture | Slide 2 |
| 3:40 | 2.2 Selection rule and tests | `selection.py`, `test_selection.py`, `pytest` output |
| 4:07 | 2.4 Decisions | Slide 3 |
| 4:36 | 2.5 Close | Slide 3 |

Differences from the script below:

- **2.3 API is not in the audio.** The recording skips it. Set `INCLUDE_API=1` if you record that section later, and the cue times will need redoing.
- **2.4 open items are not clearly in the audio.** The transcript of that part is garbled, so slide 3's "Not yet established" list may go unspoken. Check it.
- **The buffer on screen differs from the number you say.** In 1.1 you say 4,300 MW (all-January basis), but the portal opens on "Errors known at the cutoff", which shows 4,788 MW for 2026-01-15. The audio says nothing about switching basis before 1.4.
- **No part cards.** The audio has no pause between parts, so the video runs straight through. `demo/out/chapters.json` still marks where Part 2 starts (about 2:53).

If you re-record the audio, update the `CUE` table at the top of `demo/record.mjs`.

---

## Part 1: Client (about 4 min)

### 1.1 Slide 1, the finding (0:00 to 0:40)

**Screen:** `slides.html`, slide 1. Stay on it.

**Say:**
> Every day you commit to day-ahead power for tomorrow, using a wind forecast. The question is how far off that forecast tends to be, and how much to hold back because of it.
>
> In January 2026, the forecast available at 09:00 the day before ran high. It overshot actual wind output by about 1,850 megawatts on average. Holding back 4,300 megawatts would have covered 90 percent of the half-hours we could score.
>
> I'll show you how that number is built, and how far to trust it.

### 1.2 Portal overview (0:40 to 1:20)

**Screen:** switch to the portal. Point at the header, then the four controls.

**Say:**
> This is the portal. Top right is the data snapshot every number comes from, with its fetch time, so any result can be reproduced.
>
> You choose a delivery day, the cutoff on the day before, how confident you want the buffer to be, and what history the buffer is based on.

### 1.3 One day: forecast vs actual (1:20 to 2:20)

**Screen:** the chart for 2026-01-15. Hover over a couple of points. Scroll to the line under the chart about publish times.

**Say:**
> Here is one delivery day. Blue is the forecast you would have had at 09:00 on the day before. Orange is what wind actually produced.
>
> Underneath, it tells you which forecasts were used, when they were published, and how old the newest one was at the cutoff. That is the information you actually had when you made the decision, not the best forecast that existed later.
>
> Where there was no forecast at the cutoff, the gap stays a gap. Nothing is filled in.

### 1.4 Accuracy and the buffer (2:20 to 3:20)

**Screen:** the right-hand column. Point at Forecast accuracy, then the Procurement buffer card.

**Say:**
> On the right, accuracy across January: the average error, and how large the bigger misses get. Bias is forecast minus actual, so a positive number means the forecast ran high.
>
> Below that is the buffer. It answers one question: how much extra would have covered the shortfall in 90 percent of half-hours. Half-hours where wind met the forecast count as zero shortfall, so this is not "the 90th percentile of bad days".
>
> The default basis is errors known at the cutoff, so the buffer uses only history you could have had on that morning.

### 1.5 Toggle the controls (3:20 to 3:45)

**Screen:** change the confidence to P95, then the basis to "All of January (retrospective)", then change back.

**Say:**
> Raising confidence to P95 raises the buffer. The retrospective option uses all of January and is only for looking back. It could not have been known at the time.

### 1.6 How far to trust it (3:45 to 4:15)

**Screen:** point at the coverage note, then switch back to `slides.html` slide 1 and show "How far to trust it".

**Say:**
> Two cautions. Only about half the half-hours could be scored, and that count is shown on screen. And this is one month, so the extremes are rough.
>
> I have also not yet established why the forecast runs high. It could be genuine forecast bias, a mismatch in what the two datasets measure, or a timestamp offset. That is the next check, before anyone relies on this number.

---

## Part 2: Tech lead (about 4 min)

### 2.1 Slide 2, architecture (0:00 to 1:10)

**Screen:** `slides.html`, slide 2.

**Say:**
> Now the design. Data comes from Elexon only: `WINDFOR` for forecasts and `FUELHH` for actuals.
>
> Ingest fetches in chunks, normalises to UTC, and dedupes. It writes an immutable snapshot: parquet files plus a manifest with the fetch time.
>
> FastAPI reads the snapshot and applies the selection rule, the metrics and the buffer. React renders it.
>
> The key decision is that nothing calls Elexon at runtime. Results depend only on the snapshot and the cutoff, so every number is reproducible and the API is fast.
>
> It runs on Render and Vercel, and locally with Docker.

### 2.2 The selection rule and tests (1:10 to 2:10)

**Screen:** open `backend/app/analysis/selection.py`, then `backend/tests/test_selection.py`. Run `make test` in a terminal and let it finish.

**Say:**
> The core rule is in this file. For each half-hour of the delivery day, take the latest forecast published at or before the cutoff. If there is none, the target is missing.
>
> The rule and the metrics are unit tested against small hand-built fixtures, so the expected answers can be checked by hand.

### 2.3 API (2:10 to 2:50)

**Screen:** open `localhost:8000/docs`. Expand `/api/forecast/{delivery_day}`, `/api/metrics` and `/api/buffer/{delivery_day}`. Run one.

**Say:**
> Three endpoints. Forecast for a day, metrics for a range, and a buffer for a day. Every response carries the snapshot ID, and a coverage block with targets, scored, and how many had no forecast or no actual.
>
> Inputs are validated: dates must fall in January 2026, quantiles between 0 and 1, and the cutoff must be HH:MM.

### 2.4 Slide 3, decisions and open items (2:50 to 3:50)

**Screen:** `slides.html`, slide 3.

**Say:**
> The decisions. Latest forecast at or before the cutoff, because that matches what the buyer knew. A buffer that includes zero-shortfall half-hours, so it reads as "covers 90 percent of half-hours". And immutable snapshots, which are reproducible but stale until re-ingested.
>
> What is not yet established. Revisions: two pulls of the same window were identical, but the window is ten months old, so first publication is untested. And the source of the bias. The next checks are a timestamp shift, then forecast against actual by wind level.

### 2.5 Close (3:50 to 4:05)

**Say:**
> That is the pilot: reproducible, tested, and honest about its limits. Thank you.

---

## Checklist before you hit record

- [ ] Numbers on slide 1 and in 1.1 still match the portal (retrospective basis).
- [ ] Narration numbers (such as "about half") match what the portal shows for the coverage note.
- [ ] Timing: run through each part once with a timer. Cut 1.5 and the P95 toggle first if you are over.
- [ ] If the timestamp-shift check changes the story, rewrite 1.6 and the second half of 2.4.
