#!/bin/bash
# HTTP smoke tests against a running server. Usage: smoke.sh <site>
S=$1; B=http://127.0.0.1:8000; H="Host: $S"; J=/tmp/cj_$S; rm -f $J
code() { curl -s -o /tmp/body -w "%{http_code}" -H "$H" -b $J -c $J "$@"; }
check() { local want=$1 label=$2; shift 2; local got=$(code "$@"); local ok=PASS; [[ "$got" == $want ]] || ok=FAIL; printf "%-5s %-3s %s\n" "$ok" "$got" "$label"; [[ $ok == FAIL ]] && head -c 300 /tmp/body && echo; }

echo "== guest"
check 200 "public property search page /properties" $B/properties
check 200 "public listings app /listings" $B/listings
check 200 "contact page /contact" $B/contact
check 200 "frappe login page renders (asset stub ok)" $B/login
check "30[123]" "tenant portal requires login" $B/tenant-portal
check "30[123]" "admin console /re-portal requires login" $B/re-portal
check 200 "new listings search API" "$B/api/method/thinknxg_estate.portal.api.listings.search"
check 200 "LEGACY listings search API path (re_portal.*)" "$B/api/method/re_portal.api.listings.search"
check 403 "LEGACY Property Finder feed path is still gated (no token)" "$B/api/method/re_portal.api.feeds.property_finder"
check 200 "LEGACY Meta webhook verify handshake (re_voice.*)" "$B/api/method/re_voice.api.webhook.webhook?hub.mode=subscribe&hub.verify_token=test-verify-token-123&hub.challenge=4242"
grep -q 4242 /tmp/body && echo "PASS     webhook echoed the challenge" || echo "FAIL     webhook challenge missing"
check 403 "webhook rejects a wrong verify token" "$B/api/method/re_voice.api.webhook.webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=1"
check 403 "webhook POST without signature rejected" -X POST -d '{}' "$B/api/method/re_voice.api.webhook.receive"
check "40[13]" "staff API refused for guests" "$B/api/method/thinknxg_estate.core.api.get_dashboard_stats"
check "40[13]" "LEGACY staff API path refused for guests" "$B/api/method/re_core.re_core.api.get_dashboard_stats"
check "40[13]" "tenant self-payment refused" -X POST -d 'token=x&installment_name=y&amount=1' "$B/api/method/re_core.re_core.tenant_portal_api.tenant_portal_pay_installment"

echo "== administrator"
code -X POST -d 'usr=Administrator&pwd=admin' $B/api/method/login >/dev/null
check 200 "dashboard stats (new path)" "$B/api/method/thinknxg_estate.core.api.get_dashboard_stats"
check 200 "dashboard stats (LEGACY re_core path)" "$B/api/method/re_core.re_core.api.get_dashboard_stats"
check 200 "CRM deals list (LEGACY re_crm path)" "$B/api/method/re_crm.re_crm.api.get_deals_list"
check 200 "admin console page /re-portal" $B/re-portal
check 200 "workspace data: thinkNXG Estate" "$B/api/method/frappe.desk.desktop.get_desktop_page?page=%7B%22name%22%3A%22thinkNXG%20Estate%22%2C%22title%22%3A%22thinkNXG%20Estate%22%7D"
check 200 "rent roll report" "$B/api/method/frappe.desk.query_report.run?report_name=Rent%20Roll"
check 200 "voice command analytics report" "$B/api/method/frappe.desk.query_report.run?report_name=Voice%20Command%20Analytics"
check 200 "agent leaderboard report" "$B/api/method/frappe.desk.query_report.run?report_name=Agent%20Leaderboard"
check 200 "number card doc: total leads" "$B/api/method/frappe.client.get?doctype=Number%20Card&name=RE%20Total%20Leads"
check 403 "tenant portal refuses non-tenant staff" $B/tenant-portal

echo "== tenant (session login)"
rm -f $J; code -X POST -d "usr=smoke.tenant@example.com&pwd=Smoke%23Tenant2026" $B/api/method/login >/dev/null
for p in /tenant-portal /tenant-portal/lease /tenant-portal/payments /tenant-portal/maintenance; do check 200 "tenant page $p" $B$p; done
check 200 "own lease via REST" "$B/api/resource/Lease%20Contract/${OWN_LEASE}"
check 403 "another tenant's lease via REST is refused" "$B/api/resource/Lease%20Contract/${OTHER_LEASE}"
check 200 "lease list is filtered to own" "$B/api/resource/Lease%20Contract?fields=%5B%22name%22%5D&limit_page_length=100"
grep -q "${OTHER_LEASE}" /tmp/body && echo "FAIL     other tenant's lease leaked into list" || echo "PASS     list contains no other tenant's lease"
check "40[13]" "tenant cannot read staff dashboard API" "$B/api/method/thinknxg_estate.core.api.get_dashboard_stats"
check 200 "tenant dashboard API" "$B/api/method/thinknxg_estate.portal.api.tenant.dashboard"

echo "== guest listing detail"
rm -f $J
check 200 "published listing page /${LISTING_ROUTE}" "$B/${LISTING_ROUTE}"
