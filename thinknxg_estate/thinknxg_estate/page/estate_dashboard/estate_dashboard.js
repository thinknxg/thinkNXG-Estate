frappe.pages["estate-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("thinkNXG Estate Dashboard"),
		single_column: true,
	});
	new EstateDashboard(page);
};

class EstateDashboard {
	constructor(page) {
		this.page = page;
		this.charts = {};
		this.$body = $(`<div class="estate-dash"></div>`).appendTo(page.main);
		this.make_filters();
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.refresh();
	}

	make_filters() {
		const today = frappe.datetime.get_today();
		this.filters = {
			company: this.page.add_field({ fieldname: "company", label: __("Company"), fieldtype: "Link",
				options: "Company", change: () => this.refresh() }),
			property: this.page.add_field({ fieldname: "property", label: __("Property"), fieldtype: "Link",
				options: "Property", change: () => this.refresh() }),
			city: this.page.add_field({ fieldname: "city", label: __("City"), fieldtype: "Data",
				change: () => this.refresh() }),
			from_date: this.page.add_field({ fieldname: "from_date", label: __("From"), fieldtype: "Date",
				default: frappe.datetime.month_start(frappe.datetime.add_months(today, -11)), change: () => this.refresh() }),
			to_date: this.page.add_field({ fieldname: "to_date", label: __("To"), fieldtype: "Date",
				default: frappe.datetime.month_end(today), change: () => this.refresh() }),
		};
	}

	values() {
		const out = {};
		Object.entries(this.filters).forEach(([k, f]) => { if (f.get_value()) out[k] = f.get_value(); });
		return out;
	}

	refresh() {
		frappe.call({
			method: "thinknxg_estate.core.dashboard.get_overview",
			args: this.values(),
			freeze: false,
			callback: (r) => r.message && this.render(r.message),
		});
	}

	render({ kpis, charts }) {
		const money = (v) => format_currency(v || 0);
		// [label, value, target]: target is ["List", doctype, filters] or ["Report", name]
		const L = (dt, f) => ["List", dt, f || {}], R = (n) => ["Report", n];
		const cards = [
			[__("Properties"), kpis.total_properties, L("Property")],
			[__("Units"), kpis.total_units, L("Unit")],
			[__("Occupied"), kpis.occupied_units, L("Unit", { status: "Occupied" })],
			[__("Vacant"), kpis.vacant_units, L("Unit", { status: "Vacant" })],
			[__("Reserved"), kpis.reserved_units, L("Unit", { status: "Reserved" })],
			[__("Occupancy"), kpis.occupancy_rate + "%", R("Property Register")],
			[__("Active Leases"), kpis.active_leases, L("Lease Contract", { docstatus: 1 })],
			[__("Expiring (90 days)"), kpis.expiring_leases, R("RE Lease Expiry")],
			[__("Tenants"), kpis.total_tenants, R("Tenant Register")],
			[__("Owners"), kpis.total_owners, L("Property Owner")],
			[__("Leads"), kpis.total_leads, L("RE Lead")],
			[__("New Enquiries"), kpis.new_enquiries, L("Listing Inquiry", { status: "New" })],
			[__("Site Visits"), kpis.site_visits, L("Site Visit")],
			[__("Deals Closed"), kpis.deals_closed, L("RE Deal", { pipeline_stage: "Won" })],
			[__("Rent Billed (Month)"), money(kpis.monthly_rent_billed), R("RE Rent Collection")],
			[__("Collected (Month)"), money(kpis.monthly_rent_collected), R("RE Rent Collection")],
			[__("Outstanding Rent"), money(kpis.outstanding_rent), R("RE Outstanding Rent")],
			[__("Open Maintenance"), kpis.open_maintenance, L("Maintenance Request", { status: "Open" })],
		];
		const esc = frappe.utils.escape_html;
		this.$body.html(`
			<style>
				.estate-dash .kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:20px}
				.estate-dash .kpi{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:12px 14px;cursor:pointer}
				.estate-dash .kpi span{font-size:12px;color:var(--text-muted)} .estate-dash .kpi strong{display:block;font-size:20px;color:#0b1f3a}
				.estate-dash .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px}
				.estate-dash .panel{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:14px}
				.estate-dash .panel h6{margin-bottom:8px;font-weight:600}
			</style>
			<div class="kpis">${cards.map(([l, v], i) => `<div class="kpi" data-i="${i}"><span>${esc(l)}</span><strong>${esc(String(v ?? 0))}</strong></div>`).join("")}</div>
			<div class="grid">
				${["rent_by_month", "occupancy_by_property", "lead_funnel", "pipeline", "revenue_by_property",
				   "property_types", "lease_expiry_by_month", "maintenance_by_status", "agent_performance"]
					.map((k) => `<div class="panel"><h6>${esc(this.title(k))}</h6><div class="chart-${k}"></div></div>`).join("")}
			</div>`);
		const filters = this.values();
		this.$body.find(".kpi").on("click", function () {
			const target = cards[$(this).attr("data-i")][2];
			if (target[0] === "List") {
				const opts = Object.assign({}, target[2]);
				if (filters.company && !["Property Owner", "RE Lead", "Listing Inquiry", "Site Visit", "RE Deal"].includes(target[1])) opts.company = filters.company;
				frappe.route_options = opts;
				frappe.set_route("List", target[1]);
			} else {
				frappe.route_options = filters;
				frappe.set_route("query-report", target[1]);
			}
		});
		this.chart("rent_by_month", "bar", charts.rent_by_month, [["billed", __("Billed")], ["collected", __("Collected")]]);
		this.chart("occupancy_by_property", "bar", charts.occupancy_by_property, [["units", __("Units")], ["occupied", __("Occupied")]]);
		this.chart("lead_funnel", "bar", charts.lead_funnel, [["value", __("Count")]]);
		this.chart("pipeline", "bar", charts.pipeline, [["value", __("Deals")]]);
		this.chart("revenue_by_property", "bar", charts.revenue_by_property, [["collected", __("Collected")]]);
		this.chart("property_types", "donut", charts.property_types, [["value", __("Properties")]]);
		this.chart("lease_expiry_by_month", "bar", charts.lease_expiry_by_month, [["value", __("Leases")]]);
		this.chart("maintenance_by_status", "donut", charts.maintenance_by_status, [["value", __("Requests")]]);
		this.chart("agent_performance", "bar", charts.agent_performance, [["deals", __("Deals")], ["won", __("Won")]]);
	}

	title(key) {
		return {
			rent_by_month: __("Rent billed vs collected"), occupancy_by_property: __("Occupancy by property"),
			lead_funnel: __("Lead conversion funnel"), pipeline: __("Sales pipeline"),
			revenue_by_property: __("Revenue by property"), property_types: __("Property categories"),
			lease_expiry_by_month: __("Lease expiries (next 12 months)"),
			maintenance_by_status: __("Maintenance by status"), agent_performance: __("Agent performance"),
		}[key];
	}

	chart(key, type, rows, series) {
		const $el = this.$body.find(`.chart-${key}`);
		if (!rows || !rows.length) {
			$el.html(`<p class="text-muted small">${__("No data for these filters.")}</p>`);
			return;
		}
		new frappe.Chart($el[0], {
			type,
			height: 240,
			colors: ["#0b1f3a", "#14b8a6", "#7c5cfc", "#f59e0b", "#ef4444", "#64748b"],
			data: {
				labels: rows.map((r) => r.label || __("(not set)")),
				datasets: series.map(([field, name]) => ({ name, values: rows.map((r) => flt(r[field])) })),
			},
		});
	}
}
