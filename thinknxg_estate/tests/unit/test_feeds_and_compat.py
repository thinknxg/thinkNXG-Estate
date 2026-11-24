"""Framework-free tests: portal feed XML and the legacy API compatibility map."""

import ast
import importlib.util
import os
import xml.etree.ElementTree as ET

from thinknxg_estate.compat import LEGACY_METHODS
from thinknxg_estate.portal.feeds.builders import build_bayut_xml, build_property_finder_xml

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

ROW = {"reference": "LST-00001", "permit_number": "RERA-123", "listing_type": "Rent",
       "unit_type": "2BR", "price": 5400, "cheques": 4, "city": "Muscat", "locality": "Qurum",
       "title": "Sea view 2BR", "description": "Bright apartment", "area_sqm": 120, "bedrooms": 2,
       "bathrooms": 2, "furnishing": "Semi Furnished", "photos": ["https://x/1.jpg"],
       "latitude": 23.6, "longitude": 58.5, "last_update": "2026-11-24 10:00:00"}
AGENT = {"name": "Agent", "email": "agent@example.com", "phone": "+96890000000",
         "photo": None, "license_no": "BRN-1"}


def test_property_finder_feed():
    root = ET.fromstring(build_property_finder_xml([ROW], AGENT, "2026-11-24 10:00:00"))
    prop = root.find("property")
    assert root.get("listing_count") == "1"
    assert prop.findtext("reference_number") == "LST-00001"
    assert prop.findtext("permit_number") == "RERA-123"
    assert prop.findtext("offering_type") == "RR"  # residential rent
    assert prop.find("price").findtext("yearly") == "5400"


def test_bayut_feed_parses():
    root = ET.fromstring(build_bayut_xml([ROW], AGENT, "2026-11-24 10:00:00"))
    assert len(list(root)) == 1


def _defined_whitelisted(module_path, func):
    """True if `func` is a top-level @frappe.whitelist function in the module file."""
    rel = module_path.split(".", 1)[1].replace(".", os.sep) + ".py"
    path = os.path.join(APP, rel)
    tree = ast.parse(open(path).read())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func:
            return any("whitelist" in ast.unparse(d) for d in node.decorator_list)
    return False


def test_every_legacy_method_maps_to_a_whitelisted_function():
    assert len(LEGACY_METHODS) >= 160
    missing = []
    for old, new in LEGACY_METHODS.items():
        assert old.split(".")[0] in ("re_core", "re_crm", "re_portal", "re_voice"), old
        module, func = new.rsplit(".", 1)
        if not _defined_whitelisted(module, func):
            missing.append(f"{old} -> {new}")
    assert not missing, missing


def test_integration_urls_registered_with_third_parties_are_kept():
    # URLs registered with Meta and with Property Finder / Bayut must keep resolving
    for legacy in ("re_voice.api.webhook.webhook", "re_voice.api.webhook.receive",
                   "re_voice.api.webhook.verify", "re_portal.api.feeds.property_finder",
                   "re_portal.api.feeds.bayut"):
        assert legacy in LEGACY_METHODS
