# thinkNXG Estate — Load Test Report

## Summary

On a single 2 vCPU / 8 GB server running the full production stack (nginx, 5 gunicorn workers,
MariaDB, Redis, background workers, scheduler) with a 1,000-unit portfolio, thinkNXG Estate
served **300 concurrent users at 57 requests/second with 95% of responses under 320 ms and no
errors**. The CPU was the limit: at 450 users it was fully used, throughput levelled off at
63 requests/second and response times rose to about 2 seconds, still with no errors.

The load generator ran on the same server and used part of its CPU, so a dedicated 2 vCPU server
handles somewhat more than these figures.

## Environment

| Item | Value |
|---|---|
| Server | 2 vCPU, 8 GB RAM, SSD (container) |
| Software | thinkNXG Framework 16.60.2, thinkNXG ERP 16.60.0, thinkNXG Estate 1.2.0-dev, Python 3.14, MariaDB 10.11, Redis 7, nginx 1.24 |
| Processes | gunicorn `-w 5 --preload`, 1 short + 1 long worker, scheduler, Socket.IO (supervisor) |
| Site | `developer_mode` off, scheduler on |
| Data | 50 properties, 1,000 units, 400 active leases with rent schedules, deposits and draft PDCs, 1,000 CRM leads, 610 live listings, plus the migrated legacy demo data |
| Tool | Locust 2.47, `scripts/load/locustfile.py` |

Data was created with `thinknxg_estate.setup.load_data.seed` on a copy of the site.

## Scenario

Each simulated user waits between pages as a person would (visitors 3–8 s, staff 5–15 s).

| User | Share | What it does |
|---|---|---|
| Public visitor | 90% | Searches `/properties` with random filters, sort and paging; opens the map view and its map-points API; opens listing pages; compares three listings; occasionally sends an enquiry |
| Staff (RE Manager) | 10% | Signs in; opens the `/re-portal` console and its stats; the live dashboard API; desk lists of leases and leads; opens a lease form; runs the Rent Roll report |

Each visitor sends its own address in `X-Forwarded-For` through a test-only nginx front, so
per-visitor rate limits apply as they would to real visitors (the production nginx config ignores
that header from clients — see `DEPLOYMENT.md` §6).

## Results

| Concurrent users | Requests | Errors | Requests/s | Median | 95th percentile | 99th percentile | Max | CPU used |
|---|---|---|---|---|---|---|---|---|
| 50 | 1,854 | 0 | 10.4 | 29 ms | 63 ms | 150 ms | 247 ms | 32% |
| 100 | 3,675 | 0 | 20.5 | 30 ms | 78 ms | 150 ms | 278 ms | 36% |
| 200 | 7,011 | 0 | 39.1 | 37 ms | 130 ms | 220 ms | 700 ms | 62% |
| 300 | 10,176 | 0 | 56.7 | 80 ms | 320 ms | 450 ms | 858 ms | 86% |
| 450 | 11,333 | 0 | 63.2 | 1,800 ms | 2,500 ms | 3,100 ms | 4,002 ms | 99% |

Three minutes per stage, ramping 10 users/second (15 at 450).

### By request, at 300 users

| Request | Count | Median | 95th | 99th |
|---|---|---|---|---|
| `/properties` search page | 2,641 | 100 ms | 350 ms | 470 ms |
| `/properties` map view | 1,093 | 80 ms | 290 ms | 420 ms |
| Map points API | 1,093 | 30 ms | 240 ms | 340 ms |
| Listing page `/property/<route>` | 3,318 | 88 ms | 320 ms | 420 ms |
| Compare page | 523 | 80 ms | 290 ms | 420 ms |
| Search API | 523 | 30 ms | 270 ms | 350 ms |
| Enquiry (POST) | 88 | 130 ms | 340 ms | 530 ms |
| `/re-portal` console | 112 | 90 ms | 360 ms | 430 ms |
| Console stats API | 112 | 31 ms | 270 ms | 360 ms |
| Dashboard overview API | 139 | 75 ms | 310 ms | 380 ms |
| Desk list: Lease Contract | 118 | 24 ms | 270 ms | 360 ms |
| Desk list: RE Lead | 118 | 18 ms | 240 ms | 380 ms |
| Desk form: Lease Contract | 86 | 57 ms | 260 ms | 390 ms |
| Rent Roll report | 40 | 470 ms | 800 ms | 860 ms |
| Sign in | 30 | 240 ms | 400 ms | 650 ms |

The Rent Roll report is the slowest request; it reads every active lease and its installments.
On larger portfolios run it filtered by property or company.

## Findings fixed during testing

| Finding | Effect before the fix | Fix |
|---|---|---|
| Each `/properties` page view counted against the 120/hour limit of the public search API | A visitor paging through results, or an office sharing one IP, would be blocked from the property website | The page no longer uses the API limit; public read APIs allow 600/hour per visitor |
| The chat widget's settings call (on every public page) was limited to 120/hour | The chat button would stop loading for busy offices sharing one IP | Limit raised to 1,200/hour |
| Publishing a property queued one search-index job per listing | Making a large building live, the 1.2 upgrade patch or a bulk import could hit the 700-job queue cap and fail | Bulk listing syncs skip per-listing indexing and queue a single reindex |
| Every new CRM lead queued a scoring job | Importing more than ~700 leads at once failed with "Too many queued background jobs" | Imports skip the per-lead job (nightly scoring covers them); duplicate scoring jobs for one lead are merged |

Rate limiting through the production nginx config was checked separately: from one address,
the 21st enquiry within an hour was refused (HTTP 429) even when each request claimed a
different `X-Forwarded-For`.

## Re-running

```bash
# on a copy of the site, never production
bench --site LOAD_SITE set-config allow_load_test_data 1
bench --site LOAD_SITE console   # then: from thinknxg_estate.setup.load_data import seed; seed()
pip install locust
STAFF_USER=... STAFF_PASSWORD=... locust -f scripts/load/locustfile.py --host http://LOAD_SITE \
    --headless -u 300 -r 10 -t 5m --csv results/run300
```

Use a test-only proxy that passes `X-Forwarded-For` (example in `scripts/load/README.md`),
otherwise all simulated visitors share one rate-limit bucket.
