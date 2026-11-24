# thinkNXG Estate — Production Deployment Guide

This is the procedure used to build and run the production stack in the test environment
(see `LOAD_TEST.md` for the measured results). On thinkNXG Cloud (https://thinknxgcloud.com)
steps 2–6 are done for you; install the app from the marketplace and continue at step 7.

## 1. Server sizing

| Portfolio | Staff users | vCPU | RAM | Disk | Gunicorn workers |
|---|---|---|---|---|---|
| Up to 1,000 units | Up to 25 | 2 | 8 GB | 80 GB SSD | 5 |
| Up to 5,000 units | Up to 75 | 4 | 16 GB | 160 GB SSD | 9 |
| Larger, or heavy public-site traffic | 75+ | 8+ (separate DB server) | 32 GB+ | 250 GB+ SSD | 17 |

Measured on 2 vCPU / 8 GB with 1,000 units and 610 live listings: about 300 concurrent users
(90% public visitors, 10% staff) at 57 requests/second with 95% of responses under 320 ms and
no errors; the CPU was the limit (details in `LOAD_TEST.md`). Workers follow
`2 × vCPU + 1`. Keep the database on the same SSD-backed host until you outgrow one server.

## 2. Operating system packages

Ubuntu 24.04 LTS (or Debian 12): Python 3.14, Node 24, Yarn, MariaDB 10.11+, Redis 7, nginx,
supervisor, wkhtmltopdf (patched Qt build for PDF printing), git, cron. MariaDB settings:

```ini
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
innodb_buffer_pool_size = 2G      # about 25% of RAM on a shared server
```

## 3. Bench and apps

Run as a normal user (not root):

```bash
bench init --frappe-branch version-16 --frappe-path https://github.com/thinknxg/thinkNXG frappe-bench
cd frappe-bench
bench get-app --branch version-16 https://github.com/thinknxg/thinkNXG-ERP
bench get-app --branch version-16 https://github.com/thinknxg/thinkNXG-Estate
bench new-site estate.example.com --admin-password '<strong password>' --install-app erpnext
bench --site estate.example.com install-app thinknxg_estate
bench --site estate.example.com set-config developer_mode 0
bench build
```

Complete the thinkNXG ERP setup wizard (company, currency OMR, fiscal year, chart of accounts)
before going further.

> **Asset build note.** The framework's chart components are installed from GitHub during
> `bench build`. A build server that cannot reach `codeload.github.com` fails at the "island
> toolchain" step; allow that host, or install the toolchain once with
> `yarn install --production=false --cwd apps/frappe/island-toolchain` from a machine that can.

## 4. nginx, supervisor and processes

```bash
sudo bench setup production <bench-user> --yes
```

This writes `config/nginx.conf` and `config/supervisor.conf`, links them into `/etc`, and starts:

| Process | Purpose |
|---|---|
| `frappe-web` (gunicorn) | Desk, API and website pages |
| `node-socketio` | Real-time updates in the desk |
| `frappe-schedule` | Scheduled jobs (rent invoicing, reminders, statements…) |
| `short-worker`, `long-worker` | Background jobs (WhatsApp webhooks on short, lead scoring and reindexing on long) |

Turn the scheduler on: `bench --site estate.example.com enable-scheduler`.

For more than ~150 concurrent public visitors raise nginx `worker_connections` (4096) in
`/etc/nginx/nginx.conf`. To change the gunicorn worker count:
`bench config set-common-config -c gunicorn_workers 9 && bench setup supervisor --yes && sudo supervisorctl reload`.

## 5. HTTPS

```bash
bench config dns_multitenant on
bench setup add-domain --site estate.example.com estate.example.com
sudo bench setup lets-encrypt estate.example.com
```

The WhatsApp webhook and the owner/tenant portals need HTTPS.

## 6. Behind a load balancer or CDN

Per-visitor rate limits (enquiries 20/hour, sign-in attempts, public search API) use the visitor's
IP address. nginx passes the address it sees as `X-Forwarded-For`. If a load balancer or CDN sits
in front, nginx would see only the balancer's address and every visitor would share one limit.
Tell nginx to trust the balancer and use the real client address:

```nginx
# /etc/nginx/conf.d/real-ip.conf
set_real_ip_from 10.0.0.0/8;          # your load balancer's address range
real_ip_header X-Forwarded-For;
real_ip_recursive on;
```

Never pass the client's own `X-Forwarded-For` straight through to the app; anyone could then
pick their own rate-limit bucket.

## 7. Outbound connections

Allow HTTPS to: `graph.facebook.com` (WhatsApp Cloud API), the AI provider in *AI Settings*
(`api.anthropic.com`, `api.openai.com` or `generativelanguage.googleapis.com`), the map tile
server in *RE Portal Settings* (OpenStreetMap by default — use a commercial or self-hosted tile
service for a busy public site), and your email (SMTP) server.

## 8. Configure the app

Follow `ADMINISTRATION.md` §3 (settings) and §4 (roles). Before go-live: roles assigned, agents
linked to their users, WhatsApp templates approved by Meta, Rent Item and accounts set in
Property Settings, VAT templates on lease charges.

## 9. Backups

```bash
bench setup backups                       # cron: database every 6 hours, files daily
bench --site estate.example.com backup --with-files   # before every update
```

Copy backups off the server (S3-compatible storage or another host) and test a restore
quarterly — see `ADMINISTRATION.md` §8.

## 10. Updates

```bash
bench --site estate.example.com backup --with-files
bench update --pull --patch --build --requirements   # or: git pull per app, then the steps below
bench --site estate.example.com migrate
bench restart
```

Patches run during `migrate`. The 1.2 patches move the public website to `/properties` (with a
redirect from `/listings`) and move the chat assistant's AI key into *AI Settings*; both keep the
old values so a restore of the pre-update backup rolls them back.

Rollback: restore the backup taken before the update (`bench --site SITE restore ...`), check out
the previous app version, `bench build`, `bench restart`.

## 11. Monitoring

- **Error Log** (desk) — application errors, including failed provider calls.
- `bench doctor` — scheduler and worker health; `supervisorctl status`.
- `/var/log/nginx/access.log` with response times (`rt=`), `logs/web.error.log`, `logs/worker.error.log`.
- *AI Settings → Spend This Month* against the monthly AI budget.
- Background queue: Frappe refuses new jobs above 700 queued; a growing queue means workers are
  stopped or too few.
