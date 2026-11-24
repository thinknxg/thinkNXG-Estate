# Load testing

* `locustfile.py` — the scenario (public visitors and staff). See `docs/LOAD_TEST.md`.
* `loadtest-frontend.nginx.conf` — **test-only** nginx server that passes the client's
  `X-Forwarded-For` header through, so each simulated visitor gets its own rate-limit bucket.
  Never install it on a production server: it lets clients choose their own address.
* Test data: `thinknxg_estate.setup.load_data.seed` (needs `allow_load_test_data: 1` in the
  site config; records are named `LOADTEST …`).
