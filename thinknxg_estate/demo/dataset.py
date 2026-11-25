"""The demo storyline as plain data. Every record is fictional.

Dates are offsets in days from the day the seeder runs, so the portfolio always looks current.
Money is AED; rents are chosen so installments divide exactly (no fils drift).
"""

COMPANY = {
	"name": "Falak Prime Properties LLC",
	"abbr": "FPP",
	"tax_id": "100-0000-0000-003",   # fictional placeholder, not a real TRN
	"city": "Dubai",
	"domain": "Real Estate",
}
BANK = "Gulf Mercantile Bank"        # fictional
PDC_BANKS = ["Gulf Mercantile Bank", "Desert Rose Bank", "Crescent Trust Bank", "Meridian National Bank",
             "Harbour Commercial Bank"]
TAG = "demo-data"
EMAIL_DOMAIN = "falakprime.example.com"

AMENITIES = ["Covered Parking", "Swimming Pool", "Gym", "Central A/C", "Balcony", "Maid Room", "Security 24/7",
             "Elevator", "Kids Play Area", "Garden", "Built-in Wardrobes", "Pets Allowed", "Concierge",
             "Sauna", "Business Lounge", "Retail Podium"]

OWNERS = [
	dict(key="fatima", name="Fatima Al Suwaidi", type="Individual", mobile="+971 50 555 0101", fee=5,
	     portal=True, bank="Desert Rose Bank", iban="AE070000000000000000101"),
	dict(key="zenith", name="Zenith Holdings FZ-LLC", type="Company", mobile="+971 4 555 0102", fee=7,
	     portal=True, bank="Gulf Mercantile Bank", iban="AE070000000000000000102"),
	dict(key="rashid", name="Rashid Al Falasi", type="Individual", mobile="+971 50 555 0103", fee=6,
	     portal=False, bank="Crescent Trust Bank", iban="AE070000000000000000103"),
	dict(key="khalid", name="Khalid Al Mansoori", type="Individual", mobile="+971 55 555 0104", fee=8,
	     portal=False, bank="Meridian National Bank", iban="AE070000000000000000104"),
]

# ---- properties and units -------------------------------------------------------------------
# unit: (no, type, beds, baths, sqm, furnishing, parking, annual_rent, extra)
PROPERTIES = [
	dict(key="marina", name="Marina Crest Residences", type="Apartment Building", ownership="Company", owner=None,
	     city="Dubai", area="Dubai Marina", lat=25.0805, lng=55.1403, floors=42, usage="Residential",
	     address="Marina Walk, Dubai Marina, Dubai", live=True, featured=True, palette="dusk", towers=6,
	     rera="DEMO-RERA-1001", fee=None, onetime=0,
	     amenities=["Swimming Pool", "Gym", "Central A/C", "Security 24/7", "Elevator", "Covered Parking",
	                "Concierge", "Balcony", "Sauna"],
	     blurb="Waterfront living in a 42-storey tower on the Marina Walk, with a resort-style pool deck.",
	     units=[
		     ("M-0803", "Studio", 0, 1, 48, "Fully Furnished", 1, 60000, {}),
		     ("M-1204", "1BR", 1, 2, 82, "Semi Furnished", 1, 96000, {}),
		     ("M-1507", "2BR", 2, 3, 128, "Unfurnished", 2, 148000, {}),
		     ("M-2210", "2BR", 2, 3, 134, "Semi Furnished", 2, 144000, {}),
		     ("M-2706", "1BR", 1, 2, 86, "Fully Furnished", 1, 108000, {"featured": True}),
		     ("M-3001", "3BR", 3, 4, 196, "Unfurnished", 2, 204000, {"featured": True}),
		     ("M-3604", "2BR", 2, 3, 131, "Semi Furnished", 2, 156000, {}),
		     ("M-3802", "Penthouse", 4, 5, 412, "Fully Furnished", 3, 360000, {"featured": True}),
		     ("M-4001", "2BR", 2, 3, 131, "Semi Furnished", 2, 150000, {"sale": True}),
	     ]),
	dict(key="palm", name="Palm Meadows Villas", type="Villa Compound", ownership="Landlord", owner="fatima",
	     city="Dubai", area="Dubai Hills Estate", lat=25.1124, lng=55.2447, floors=2, usage="Residential",
	     address="Hills Park Road, Dubai Hills Estate, Dubai", live=True, featured=True, palette="gold", towers=5,
	     low_rise=True, rera="DEMO-RERA-1002", fee=5, onetime=2000,
	     amenities=["Garden", "Swimming Pool", "Maid Room", "Covered Parking", "Kids Play Area", "Security 24/7",
	                "Pets Allowed", "Central A/C"],
	     blurb="A gated compound of family villas with private gardens, close to schools and the golf course.",
	     units=[
		     ("V-01", "3BR", 3, 4, 310, "Unfurnished", 2, 228000, {"floor": "Ground Floor"}),
		     ("V-02", "4BR+", 4, 5, 420, "Semi Furnished", 3, 336000, {"floor": "Ground Floor"}),
		     ("V-03", "4BR+", 5, 6, 455, "Unfurnished", 3, 360000, {"floor": "Ground Floor"}),
		     ("V-04", "3BR", 3, 4, 305, "Unfurnished", 2, 240000, {"floor": "Ground Floor", "featured": True}),
		     ("V-05", "4BR+", 4, 5, 428, "Fully Furnished", 3, 348000, {"floor": "Ground Floor"}),
		     ("V-06", "4BR+", 4, 5, 428, "Unfurnished", 3, 330000, {"floor": "Ground Floor", "sale": True}),
	     ]),
	dict(key="tower", name="Business Bay Central Tower", type="Commercial Tower", ownership="Landlord", owner="zenith",
	     city="Dubai", area="Business Bay", lat=25.1865, lng=55.2640, floors=30, usage="Commercial",
	     address="Bay Avenue, Business Bay, Dubai", live=True, featured=False, palette="day", towers=4,
	     rera="DEMO-RERA-1003", fee=7, onetime=3000,
	     amenities=["Central A/C", "Elevator", "Security 24/7", "Covered Parking", "Business Lounge",
	                "Retail Podium", "Concierge"],
	     blurb="Grade-A offices and ground-floor retail on the canal, minutes from Downtown.",
	     units=[
		     ("OF-701", "Office", 0, 2, 140, "Unfurnished", 3, 168000, {"vat": True}),
		     ("OF-702", "Office", 0, 2, 120, "Semi Furnished", 2, 144000, {"vat": True}),
		     ("OF-803", "Office", 0, 3, 180, "Unfurnished", 4, 216000, {"vat": True, "featured": True}),
		     ("OF-804", "Office", 0, 2, 160, "Semi Furnished", 3, 192000, {"vat": True}),
		     ("SH-G1", "Shop", 0, 1, 95, "Unfurnished", 2, 288000, {"vat": True}),
		     ("SH-G2", "Shop", 0, 1, 80, "Unfurnished", 1, 240000, {"vat": True}),
	     ]),
	dict(key="jvc", name="JVC Gardens Residences", type="Apartment Building", ownership="Landlord", owner="rashid",
	     city="Dubai", area="Jumeirah Village Circle", lat=25.0602, lng=55.2095, floors=9, usage="Residential",
	     address="District 14, Jumeirah Village Circle, Dubai", live=True, featured=False, palette="teal", towers=4,
	     low_rise=True, rera="DEMO-RERA-1004", fee=6, onetime=1500,
	     amenities=["Swimming Pool", "Gym", "Covered Parking", "Kids Play Area", "Security 24/7", "Elevator",
	                "Balcony", "Pets Allowed"],
	     blurb="Affordable, well-kept apartments in a green community with parks and retail on the doorstep.",
	     units=[
		     ("J-101", "Studio", 0, 1, 42, "Unfurnished", 1, 44000, {"floor": "First Floor"}),
		     ("J-102", "1BR", 1, 2, 70, "Semi Furnished", 1, 62000, {"floor": "First Floor"}),
		     ("J-203", "1BR", 1, 2, 74, "Unfurnished", 1, 66000, {"floor": "Second Floor"}),
		     ("J-204", "2BR", 2, 3, 108, "Semi Furnished", 1, 90000, {"floor": "Second Floor"}),
		     ("J-305", "2BR", 2, 3, 112, "Unfurnished", 2, 96000, {"floor": "Third Floor"}),
		     ("J-306", "Studio", 0, 1, 44, "Fully Furnished", 1, 48000, {"floor": "Third Floor"}),
	     ]),
	dict(key="lofts", name="Downtown Skyline Lofts", type="Mixed Use", ownership="Landlord", owner="khalid",
	     city="Dubai", area="Downtown Dubai", lat=25.1972, lng=55.2744, floors=24, usage="Residential",
	     address="Boulevard Plaza, Downtown Dubai", live=True, featured=True, palette="night", towers=5,
	     rera="DEMO-RERA-1005", fee=8, onetime=3000,
	     amenities=["Swimming Pool", "Gym", "Concierge", "Security 24/7", "Elevator", "Covered Parking",
	                "Central A/C", "Balcony", "Retail Podium"],
	     blurb="Designer lofts above a street-level retail arcade, with views of the Downtown skyline.",
	     units=[
		     ("L-1A", "1BR", 1, 2, 88, "Fully Furnished", 1, 112000, {}),
		     ("L-2B", "2BR", 2, 3, 136, "Semi Furnished", 2, 170000, {}),
		     ("L-3C", "2BR", 2, 3, 140, "Semi Furnished", 2, 176000, {}),
		     ("L-4D", "3BR", 3, 4, 210, "Fully Furnished", 2, 236000, {"featured": True}),
		     ("L-5E", "1BR", 1, 2, 88, "Fully Furnished", 1, 114000, {"sale": True}),
		     ("S-01", "Shop", 0, 1, 70, "Unfurnished", 1, 204000, {"usage": "Commercial", "vat": True}),
		     ("S-02", "Shop", 0, 1, 64, "Unfurnished", 1, 192000, {"usage": "Commercial", "vat": True}),
	     ]),
]

# ---- tenants --------------------------------------------------------------------------------
# kyc: (id_type, number, expiry offset in days)
TENANTS = [
	dict(key="james", name="James Whitmore", nat="British", mobile="+971 50 555 0201", portal=True,
	     kyc=[("Resident Card", "784-1989-0000201-1", 410), ("Passport", "GBR-DEMO-201", 1100)]),
	dict(key="priya", name="Priya Nair", nat="Indian", mobile="+971 52 555 0202", portal=True,
	     kyc=[("Resident Card", "784-1991-0000202-2", 55), ("Passport", "IND-DEMO-202", 900)]),
	dict(key="aisha", name="Aisha Rahman", nat="Bangladeshi", mobile="+971 54 555 0203",
	     kyc=[("Resident Card", "784-1994-0000203-3", 620)]),
	dict(key="layla", name="Layla Al Zaabi", nat="Emirati", mobile="+971 50 555 0204", portal=True,
	     kyc=[("National ID", "784-1990-0000204-4", 1500)]),
	dict(key="lucas", name="Lucas Meyer", nat="German", mobile="+971 55 555 0205",
	     kyc=[("Resident Card", "784-1985-0000205-5", 700), ("Passport", "DEU-DEMO-205", 1300)]),
	dict(key="daniel", name="Daniel Okafor", nat="Nigerian", mobile="+971 56 555 0206",
	     kyc=[("Resident Card", "784-1992-0000206-6", 25)]),
	dict(key="ahmed", name="Ahmed Siddiqui", nat="Pakistani", mobile="+971 50 555 0207",
	     kyc=[("Resident Card", "784-1988-0000207-7", 340)]),
	dict(key="chen", name="Chen Wei", nat="Chinese", mobile="+971 52 555 0208",
	     kyc=[("Resident Card", "784-1993-0000208-8", 480), ("Visa", "VISA-DEMO-208", 480)]),
	dict(key="sofia", name="Sofia Marquez", nat="Spanish", mobile="+971 54 555 0209",
	     kyc=[("Resident Card", "784-1990-0000209-9", 200)]),
	dict(key="marcus", name="Marcus Lindqvist", nat="Swedish", mobile="+971 55 555 0210",
	     kyc=[("Resident Card", "784-1984-0000210-0", 560), ("Passport", "SWE-DEMO-210", 1450)]),
	dict(key="karim", name="Dr. Karim Nasser", nat="Jordanian", mobile="+971 50 555 0211",
	     kyc=[("Resident Card", "784-1980-0000211-1", 900)]),
	dict(key="olivia", name="Olivia Hartmann", nat="Austrian", mobile="+971 56 555 0212",
	     kyc=[("Resident Card", "784-1987-0000212-2", 150)]),
	dict(key="blueorbit", name="BlueOrbit Technologies FZ-LLC", type="Company", mobile="+971 4 555 0213",
	     nat="UAE", kyc=[("CR License", "DEMO-TL-440213", 210)]),
	dict(key="nimbus", name="Nimbus Legal Consultants", type="Company", mobile="+971 4 555 0214", nat="UAE",
	     kyc=[("CR License", "DEMO-TL-440214", 330)]),
	dict(key="saffron", name="Saffron & Sage Cafe LLC", type="Company", mobile="+971 4 555 0215", nat="UAE",
	     kyc=[("CR License", "DEMO-TL-440215", 40)]),
	dict(key="horizon", name="Horizon Dental Clinic LLC", type="Company", mobile="+971 4 555 0216", nat="UAE",
	     kyc=[("CR License", "DEMO-TL-440216", 380)]),
	dict(key="omar", name="Omar Haddad", nat="Jordanian", mobile="+971 55 555 0217",
	     kyc=[("Resident Card", "784-1986-0000217-7", 520)]),
	dict(key="elena", name="Elena Petrova", nat="Russian", mobile="+971 52 555 0218",
	     kyc=[("Resident Card", "784-1991-0000218-8", 260), ("Passport", "RUS-DEMO-218", 800)]),
	dict(key="mariam", name="Mariam Qureshi", nat="Pakistani", mobile="+971 54 555 0219",
	     kyc=[("Resident Card", "784-1989-0000219-9", -20)]),
	dict(key="natalia", name="Natalia Ivanova", nat="Ukrainian", mobile="+971 56 555 0220",
	     kyc=[("Resident Card", "784-1995-0000220-0", 700)]),
]

# ---- leases ---------------------------------------------------------------------------------
# months: term; freq: Annual / Semi-Annual / Quarterly / Monthly
# over: installment index -> outcome code
#   P cheque cleared | C cash | H part-paid in cash (frac) | O overdue | I invoiced, not yet due/paid
#   B cheque bounced | R cheque in hand (future) | D cheque deposited, clearing | _ nothing yet
# deposit: security deposit (AED); state: Active/Expiring/Expired/Terminated/Renewed/Draft
LEASES = [
	dict(key="l_m1204", unit="M-1204", tenant="james", start=-150, months=12, freq="Quarterly",
	     deposit=5000, over={2: "R", 3: "R"}, inspect_in=True),
	dict(key="l_m1507", unit="M-1507", tenant="priya", start=-300, months=12, freq="Semi-Annual",
	     deposit=7500, over={}, state="Expiring", inspect_in=True),
	dict(key="l_m0803", unit="M-0803", tenant="aisha", start=-90, months=12, freq="Monthly",
	     deposit=3000, over={2: "O", 3: "I"}, mode_pay="cash_mix"),
	dict(key="l_m2210_old", unit="M-2210", tenant="layla", start=-420, months=12, freq="Semi-Annual",
	     deposit=7000, over={}, state="Renewed"),
	dict(key="l_m2210", unit="M-2210", tenant="layla", start=-54, months=12, freq="Semi-Annual",
	     deposit=7200, over={}, renew_of="l_m2210_old"),
	dict(key="l_m3802", unit="M-3802", tenant="lucas", start=-45, months=12, freq="Annual",
	     deposit=18000, over={}, won=True, inspect_in=True),
	dict(key="l_j101", unit="J-101", tenant="daniel", start=-240, months=12, freq="Quarterly",
	     deposit=2200, over={2: "H"}, bulk_settle=True),
	dict(key="l_j102", unit="J-102", tenant="ahmed", start=-330, months=12, freq="Semi-Annual",
	     deposit=3100, over={1: "B"}, state="Expiring"),
	dict(key="l_j203", unit="J-203", tenant="chen", start=-100, months=12, freq="Quarterly",
	     deposit=3300, over={1: "O"}),
	dict(key="l_j204", unit="J-204", tenant="sofia", start=-200, months=12, freq="Quarterly",
	     deposit=4500, over={2: "O"}, state="Terminated", terminate=-15, inspect_out=True),
	dict(key="l_v01", unit="V-01", tenant="marcus", start=-170, months=12, freq="Semi-Annual",
	     deposit=11400, over={1: "R"}, inspect_in=True),
	dict(key="l_v02", unit="V-02", tenant="karim", start=-25, months=12, freq="Quarterly",
	     deposit=16800, over={}, won=True, inspect_in=True),
	dict(key="l_v03", unit="V-03", tenant="olivia", start=-280, months=12, freq="Annual",
	     deposit=18000, over={}, state="Expiring"),
	dict(key="l_of701", unit="OF-701", tenant="blueorbit", start=-120, months=12, freq="Quarterly",
	     deposit=16800, over={}, vat=True),
	dict(key="l_of702", unit="OF-702", tenant="nimbus", start=-60, months=12, freq="Semi-Annual",
	     deposit=14400, over={}, vat=True, won=True),
	dict(key="l_shg1", unit="SH-G1", tenant="saffron", start=-330, months=12, freq="Quarterly",
	     deposit=28800, over={3: "O"}, vat=True, state="Expiring"),
	dict(key="l_shg2", unit="SH-G2", tenant="horizon", start=-20, months=12, freq="Annual",
	     deposit=24000, over={}, vat=True, won=True),
	dict(key="l_l1a", unit="L-1A", tenant="omar", start=-75, months=12, freq="Quarterly",
	     deposit=5600, over={}, won=True, inspect_in=True),
	dict(key="l_l2b", unit="L-2B", tenant="elena", start=-190, months=12, freq="Semi-Annual",
	     deposit=8500, over={1: "H"}),
	dict(key="l_l3c", unit="L-3C", tenant="mariam", start=-400, months=12, freq="Quarterly",
	     deposit=8800, over={}, state="Expired", inspect_out=True),
	dict(key="l_j305_draft", unit="J-305", tenant="natalia", start=14, months=12, freq="Quarterly",
	     deposit=4800, over={}, state="Draft"),
]

# ---- CRM -------------------------------------------------------------------------------------
AGENTS = [
	dict(key="rania", name="Rania Khoury", email="rania.khoury", mobile="+971 50 555 0301", type="Employee Agent",
	     comm=("Percent", 2.0), roles=["RE Sales Agent"], target=(4, 600000)),
	dict(key="tariq", name="Tariq Mahmood", email="tariq.mahmood", mobile="+971 55 555 0302", type="Employee Agent",
	     comm=("Tiered", None), roles=["RE Sales Agent"], target=(4, 500000)),
	dict(key="hannah", name="Hannah Fischer", email="hannah.fischer", mobile="+971 52 555 0303",
	     type="Employee Agent", comm=("Flat", 1500), roles=["RE Sales Agent"], target=(3, 400000)),
	dict(key="vikram", name="Vikram Anand", email="vikram.anand", mobile="+971 56 555 0304", type="Employee Agent",
	     comm=("Percent", 2.5), roles=["RE Sales Agent"], target=(4, 650000)),
	dict(key="samir", name="Samir Bakr", email="samir.bakr", mobile="+971 50 555 0305", type="External Broker",
	     brokerage="Gulf Anchor Realty", licence="DEMO-BRK-2201", comm=("Percent", 3.0), roles=["Broker"],
	     target=(2, 300000)),
	dict(key="nadia", name="Nadia Farouk", email="nadia.farouk", mobile="+971 54 555 0306", type="External Broker",
	     brokerage="Skyline Partners Brokerage", licence="DEMO-BRK-2202", comm=("Percent", 2.75),
	     roles=["Broker"], target=(2, 300000)),
]
SLABS = [(0, 100000, 1.5), (100000.01, 250000, 2.0), (250000.01, 99999999, 2.5)]

STAFF = [
	dict(email="layla.haddad", name="Layla Haddad", roles=["RE Manager", "Accounts Manager", "Leasing Manager"],
	     title="Portfolio Director"),
	dict(email="omar.sabri", name="Omar Sabri", roles=["Property Manager", "Leasing Officer", "Maintenance Supervisor"],
	     title="Property Manager"),
	dict(email="salma.nour", name="Salma Nour", roles=["Accounts User", "Accounts Manager"], title="Accountant"),
]

# lead: name, mobile, source, agent, interest, type, location, budget(min,max), beds, status, days_ago, extras
# deal stage: None or stage; unit: target unit; lost reason for Lost
LEADS = [
	# --- converted to leases (Won)
	dict(name="Lucas Meyer", mobile="+971 55 555 0205", src="Property Finder", agent="rania", type="Apartment",
	     loc="Dubai Marina", budget=(300000, 380000), beds=4, status="Converted", ago=75, stage="Won", unit="M-3802", lease="l_m3802"),
	dict(name="Omar Haddad", mobile="+971 55 555 0217", src="Bayut", agent="tariq", type="Apartment", loc="Downtown Dubai",
	     budget=(100000, 125000), beds=1, status="Converted", ago=110, stage="Won", unit="L-1A", lease="l_l1a"),
	dict(name="Dr. Karim Nasser", mobile="+971 50 555 0211", src="Referral", agent="hannah", type="Villa", loc="Dubai Hills Estate",
	     budget=(300000, 360000), beds=4, status="Converted", ago=60, stage="Won", unit="V-02", lease="l_v02", loan=False),
	dict(name="Horizon Dental Clinic LLC", mobile="+971 4 555 0216", src="Walk-in", agent="vikram", type="Shop", loc="Business Bay",
	     budget=(200000, 260000), beds=0, status="Converted", ago=55, stage="Won", unit="SH-G2", lease="l_shg2"),
	dict(name="Nimbus Legal Consultants", mobile="+971 4 555 0214", src="Website", agent="samir", type="Office", loc="Business Bay",
	     budget=(130000, 160000), beds=0, status="Converted", ago=95, stage="Won", unit="OF-702", lease="l_of702"),
	# --- reservation stage
	dict(name="Ingrid Solberg", mobile="+971 50 555 0401", src="WhatsApp", agent="rania", type="Villa", loc="Dubai Hills Estate",
	     budget=(330000, 370000), beds=4, status="Qualified", ago=21, stage="Reservation", unit="V-05", fee=20000),
	dict(name="Meridian Analytics DMCC", mobile="+971 4 555 0402", src="Referral", agent="vikram", type="Office", loc="Business Bay",
	     budget=(180000, 210000), beds=0, status="Qualified", ago=30, stage="Reservation", unit="OF-804", fee=15000),
	# --- negotiation
	dict(name="Rohan Mehta", mobile="+971 52 555 0403", src="Property Finder", agent="tariq", type="Apartment", loc="Dubai Marina",
	     budget=(190000, 215000), beds=3, status="Qualified", ago=18, stage="Negotiation", unit="M-3001"),
	dict(name="Amelia Grant", mobile="+971 54 555 0404", src="Bayut", agent="hannah", type="Apartment", loc="Downtown Dubai",
	     budget=(220000, 250000), beds=3, status="Qualified", ago=14, stage="Negotiation", unit="L-4D"),
	dict(name="Yusuf Al Hosani", mobile="+971 50 555 0405", src="Referral", agent="nadia", type="Villa", loc="Dubai Hills Estate",
	     budget=(230000, 260000), beds=3, status="Qualified", ago=12, stage="Negotiation", unit="V-04"),
	# --- site visit scheduled
	dict(name="Beatriz Santos", mobile="+971 56 555 0406", src="Website", agent="vikram", type="Apartment", loc="Dubai Marina",
	     budget=(100000, 115000), beds=1, status="Contacted", ago=9, stage="Site Visit Scheduled", unit="M-2706"),
	dict(name="Kenji Watanabe", mobile="+971 55 555 0407", src="Property Finder", agent="rania", type="Apartment", loc="Jumeirah Village Circle",
	     budget=(90000, 105000), beds=2, status="Contacted", ago=8, stage="Site Visit Scheduled", unit="J-305"),
	dict(name="Safiya Rahim", mobile="+971 52 555 0408", src="WhatsApp", agent="samir", type="Office", loc="Business Bay",
	     budget=(200000, 230000), beds=0, status="Contacted", ago=7, stage="Site Visit Scheduled", unit="OF-803"),
	# --- contacted
	dict(name="Thomas Becker", mobile="+971 50 555 0409", src="Bayut", agent="tariq", type="Apartment", loc="Dubai Marina",
	     budget=(140000, 165000), beds=2, status="Contacted", ago=6, stage="Contacted", unit="M-3604"),
	dict(name="Zainab Qadir", mobile="+971 54 555 0410", src="Social Media", agent="hannah", type="Apartment", loc="Jumeirah Village Circle",
	     budget=(40000, 52000), beds=0, status="Contacted", ago=5, stage="Contacted", unit="J-306"),
	dict(name="Pavel Novak", mobile="+971 56 555 0411", src="Phone Call", agent="nadia", type="Apartment", loc="Downtown Dubai",
	     budget=(160000, 185000), beds=2, status="Contacted", ago=4, stage="Contacted", unit="L-3C"),
	# --- new deals
	dict(name="Hana Kobayashi", mobile="+971 55 555 0412", src="Website", agent="vikram", type="Apartment", loc="Dubai Marina",
	     budget=(90000, 110000), beds=1, status="New", ago=2, stage="New", unit="M-2706"),
	dict(name="Michael O'Connor", mobile="+971 50 555 0413", src="Campaign", agent="rania", type="Villa", loc="Dubai Hills Estate",
	     budget=(220000, 250000), beds=3, status="New", ago=1, stage="New", unit="V-04"),
	dict(name="Leila Ibrahim", mobile="+971 52 555 0414", src="WhatsApp", agent="tariq", type="Apartment", loc="Downtown Dubai",
	     budget=(105000, 120000), beds=1, status="New", ago=1, stage="New", unit=None),
	# --- lost
	dict(name="Gregor Hansen", mobile="+971 54 555 0415", src="Property Finder", agent="rania", type="Apartment", loc="Dubai Marina",
	     budget=(70000, 85000), beds=1, status="Disqualified", ago=70, stage="Lost", unit="M-3604",
	     lost="Budget is below the lowest available rent for a 1-bedroom in the Marina."),
	dict(name="Anita Desai", mobile="+971 56 555 0416", src="Bayut", agent="hannah", type="Villa", loc="Dubai Hills Estate",
	     budget=(220000, 245000), beds=3, status="Disqualified", ago=52, stage="Lost", unit="V-04",
	     lost="Needed a pet-friendly villa with a larger garden; chose a compound in another area."),
	dict(name="Faisal Jaber", mobile="+971 50 555 0417", src="Walk-in", agent="samir", type="Office", loc="Business Bay",
	     budget=(120000, 140000), beds=0, status="Disqualified", ago=44, stage="Lost", unit="OF-803",
	     lost="Went with another broker's listing at a lower rent."),
	dict(name="Claire Dubois", mobile="+971 55 555 0418", src="Referral", agent="nadia", type="Apartment", loc="Jumeirah Village Circle",
	     budget=(80000, 95000), beds=2, status="Disqualified", ago=38, stage="Lost", unit="J-305",
	     lost="Relocation cancelled by the employer."),
	# --- leads that have no deal yet
	dict(name="Nikhil Sharma", mobile="+971 52 555 0419", src="Website", agent="vikram", type="Apartment", loc="Dubai Marina",
	     budget=(95000, 120000), beds=1, status="New", ago=0, stage=None, unit=None),
	dict(name="Reem Al Nuaimi", mobile="+971 50 555 0420", src="WhatsApp", agent="rania", type="Villa", loc="Dubai Hills Estate",
	     budget=(230000, 270000), beds=3, status="New", ago=0, stage=None, unit=None),
	dict(name="Stefan Berg", mobile="+971 56 555 0421", src="Property Finder", agent="tariq", type="Apartment", loc="Downtown Dubai",
	     budget=(120000, 150000), beds=2, status="Contacted", ago=3, stage=None, unit=None),
	dict(name="Ayesha Malik", mobile="+971 54 555 0422", src="Social Media", agent="hannah", type="Apartment", loc="Jumeirah Village Circle",
	     budget=(55000, 70000), beds=1, status="Qualified", ago=4, stage=None, unit=None, loan=False),
	dict(name="Jonas Weber", mobile="+971 55 555 0423", src="Bayut", agent="nadia", type="Apartment", loc="Dubai Marina",
	     budget=(2300000, 2800000), beds=2, status="Qualified", ago=6, stage=None, unit=None, interest="Buy", loan=True),
	dict(name="Salma Idris", mobile="+971 52 555 0424", src="Referral", agent="samir", type="Villa", loc="Dubai Hills Estate",
	     budget=(4200000, 5200000), beds=4, status="Qualified", ago=10, stage=None, unit=None, interest="Buy", loan=True),
	dict(name="Victor Alvarez", mobile="+971 50 555 0425", src="Phone Call", agent="vikram", type="Shop", loc="Downtown Dubai",
	     budget=(170000, 210000), beds=0, status="Contacted", ago=11, stage=None, unit=None),
	dict(name="Dina Karam", mobile="+971 56 555 0426", src="Campaign", agent="rania", type="Apartment", loc="Dubai Marina",
	     budget=(80000, 95000), beds=1, status="Disqualified", ago=33, stage=None, unit=None),
]

# site visits: (lead name, offset days, hour, outcome, feedback)
VISITS = [
	("Lucas Meyer", -68, 11, "Interested", "Loved the sea view; asked about a longer lease for the penthouse."),
	("Omar Haddad", -102, 16, "Interested", "Wants the furnished unit; fine with quarterly cheques."),
	("Dr. Karim Nasser", -54, 10, "Interested", "Family of five; liked the garden and the compound security."),
	("Horizon Dental Clinic LLC", -50, 12, "Interested", "Ground-floor frontage suits the clinic; plumbing points checked."),
	("Nimbus Legal Consultants", -88, 14, "Considering", "Compared with a tower in DIFC; asked for a fit-out period."),
	("Nimbus Legal Consultants", -80, 11, "Interested", "Second visit with the partners; agreed the terms."),
	("Ingrid Solberg", -17, 15, "Interested", "Wants a furnished villa; paid the booking fee."),
	("Meridian Analytics DMCC", -25, 11, "Interested", "Needs 3 parking bays; reservation placed."),
	("Rohan Mehta", -13, 17, "Considering", "Likes the unit but wants a rent reduction."),
	("Amelia Grant", -10, 12, "Considering", "Comparing with another Downtown building."),
	("Yusuf Al Hosani", -8, 10, "Interested", "Asked the landlord to include garden maintenance."),
	("Beatriz Santos", 2, 11, None, None),
	("Kenji Watanabe", 3, 16, None, None),
	("Safiya Rahman" if False else "Safiya Rahim", 4, 14, None, None),
	("Thomas Becker", -3, 18, "No Show", "Did not attend; to be rebooked."),
	("Gregor Hansen", -64, 12, "Not Interested", "Rent above budget."),
	("Anita Desai", -46, 15, "Not Interested", "Garden too small for the dogs."),
	("Faisal Jaber", -40, 11, "Not Interested", "Chose another office."),
]

# maintenance: (unit, category, priority, status, description, days_ago, supplier key, material, labor, billable,
#               completed_days_ago)
SUPPLIERS = {
	"cool": ("CoolBreeze AC Services LLC", "AC"),
	"aqua": ("AquaFix Plumbing & Sanitary", "Plumbing"),
	"volt": ("VoltEdge Electrical Contracting", "Electrical"),
	"pest": ("PestShield Control Services", "Pest Control"),
	"hands": ("BrightHands Facility Services", "Civil"),
	"util": ("Gulf Utilities Authority (Demo)", None),
	"muni": ("Metro Municipality Services (Demo)", None),
	"insure": ("Sentinel Property Insurance (Demo)", None),
}
MAINTENANCE = [
	# open
	("M-1204", "Plumbing", "Emergency", "Open", "Water dripping through the bathroom ceiling from the unit above; floor already wet.", 0, None),
	("J-203", "AC", "High", "Open", "AC is running but not cooling; the living room reaches 29 C by afternoon.", 1, None),
	("L-1A", "Civil", "Medium", "Open", "Kitchen cabinet door has come off its hinge and the drawer runner is broken.", 2, None),
	("M-0803", "Civil", "Low", "Open", "Touch-up painting needed on the bedroom wall after a minor leak repair.", 3, None),
	("V-01", "Electrical", "High", "Open", "Circuit breaker for the upstairs bedrooms trips several times a day.", 1, None),
	("SH-G1", "Appliances", "Medium", "Open", "Display refrigerator in the shop is not holding temperature.", 4, None),
	# in progress (job created)
	("OF-701", "AC", "Medium", "In Progress", "Quarterly service and filter replacement for the office AC units.", 6, "cool"),
	("J-101", "Plumbing", "Medium", "In Progress", "Slow drain in the kitchen sink and a leaking mixer tap.", 5, "aqua"),
	("V-03", "Pest Control", "Medium", "In Progress", "Ants in the kitchen and garden-side doors; treatment visit scheduled.", 4, "pest"),
	# on hold
	("L-2B", "Appliances", "Low", "On Hold", "Dishwasher drain pump faulty; waiting for the spare part to arrive.", 12, None),
	# completed (owner / tenant / company billable)
	("M-1507", "AC", "High", "Completed", "AC compressor replaced after a full breakdown.", 62, "cool", 1850, 650, "Company", 60),
	("J-102", "Plumbing", "Emergency", "Completed", "Burst flexible hose under the kitchen sink flooding the floor; replaced and dried.", 48, "aqua", 240, 360, "Owner", 47),
	("V-02", "Electrical", "Medium", "Completed", "Installed outdoor lighting and replaced two faulty sockets.", 30, "volt", 620, 480, "Owner", 28),
	("L-2B", "Civil", "Low", "Completed", "Re-sealed bathroom silicone and repaired a cracked tile.", 40, "hands", 180, 320, "Tenant", 38),
	("OF-702", "Electrical", "Medium", "Completed", "Added data points and re-routed trunking for the partners' room.", 35, "volt", 1450, 900, "Owner", 33),
	("J-204", "Civil", "Low", "Completed", "Repainted the living room and fixed a door closer.", 74, "hands", 520, 780, "Owner", 70),
	("M-3802", "AC", "Emergency", "Completed", "Chiller unit failed on a hot night; emergency call-out and refrigerant top-up.", 21, "cool", 900, 700, "Company", 20),
	("L-1A", "Plumbing", "Medium", "Completed", "Replaced the shower mixer and flushed the water heater.", 56, "aqua", 540, 360, "Owner", 55),
	# rejected / cancelled
	("J-102", "Civil", "Low", "Rejected", "Request to repaint the entire apartment in a new colour (tenant preference, outside the lease terms).", 26, None),
	("L-3C", "Appliances", "Low", "Cancelled", "Microwave not working - tenant later confirmed it was unplugged.", 80, None),
]

# property expenses: (property key, days ago, type, amount, supplier key, paid_fraction, description)
EXPENSES = [
	("marina", 85, "Insurance", 42000, "insure", 1.0, "Annual building insurance premium - instalment 1"),
	("marina", 40, "Utilities", 18500, "util", 1.0, "Common-area electricity and chilled-water charges"),
	("marina", 12, "Utilities", 19800, "util", 0.5, "Common-area electricity and chilled-water charges"),
	("palm", 70, "Municipality Fee", 6500, "muni", 1.0, "Annual community service fee"),
	("palm", 30, "Staff", 9000, "hands", 1.0, "Landscaping and gate staff for the month"),
	("tower", 55, "Insurance", 28000, "insure", 1.0, "Property all-risk insurance"),
	("tower", 22, "Utilities", 24500, "util", 0.0, "Common-area power and cooling"),
	("jvc", 45, "Maintenance", 7400, "hands", 1.0, "Lift servicing and fire-system inspection"),
	("lofts", 28, "Municipality Fee", 8800, "muni", 0.6, "Annual building and parking fee"),
	("lofts", 9, "Staff", 11200, "hands", 0.0, "Concierge and security staffing for the month"),
]

# expired / terminated deposit settlements: lease key -> (deduction, reason)
DEPOSIT_SETTLEMENTS = {
	"l_j204": (1800, "Move-out inspection: wall repainting and a damaged door closer."),
	"l_l3c": (0, "No deductions: unit handed back in good condition."),
	"l_m2210_old": (0, "Rolled into the renewed lease; no deductions."),
}

PORTAL_VISITORS = [
	dict(key="hana", name="Hana Kobayashi", mobile="+971 55 555 0412", lead="Hana Kobayashi"),
	dict(key="beatriz", name="Beatriz Santos", mobile="+971 56 555 0406", lead="Beatriz Santos"),
	dict(key="nikhil", name="Nikhil Sharma", mobile="+971 52 555 0419", lead="Nikhil Sharma"),
	dict(key="kenji", name="Kenji Watanabe", mobile="+971 55 555 0407", lead="Kenji Watanabe"),
	dict(key="jonas", name="Jonas Weber", mobile="+971 55 555 0423", lead="Jonas Weber"),
]
WISHLIST = {"hana": ["M-2706", "M-3604"], "beatriz": ["M-2706", "L-4D", "M-3001"], "nikhil": ["M-2706"],
            "kenji": ["J-305", "J-306"], "jonas": []}
SAVED_SEARCHES = [
	dict(visitor="hana", location="Dubai Marina", unit_type="1BR", bedrooms=1, min_rent=80000, max_rent=115000),
	dict(visitor="kenji", location="Jumeirah Village Circle", unit_type="2BR", bedrooms=2, min_rent=85000, max_rent=105000),
	dict(visitor="nikhil", location="Dubai Marina", unit_type="1BR", bedrooms=1, min_rent=90000, max_rent=125000),
	dict(visitor="beatriz", location="Downtown Dubai", unit_type="3BR", bedrooms=3, min_rent=200000, max_rent=260000),
]
# viewing requests: (visitor, unit, days from today, slot, status)
VIEWINGS = [
	("hana", "M-2706", 3, "10:00 - 12:00", "Requested"),
	("beatriz", "M-2706", 2, "14:00 - 16:00", "Confirmed"),
	("kenji", "J-305", 3, "16:00 - 18:00", "Confirmed"),
	("nikhil", "M-2706", 5, "12:00 - 14:00", "Requested"),
	("beatriz", "L-4D", -4, "10:00 - 12:00", "Completed"),
]
ENQUIRIES = [
	("hana", "M-3604", "General Enquiry", "Is the rent negotiable for a two-year contract?", "New"),
	("nikhil", "M-2706", "Price Negotiation", "Can the rent be paid in 4 cheques instead of 2?", "Assigned"),
	("jonas", "M-3001", "General Enquiry", "Do you also have units for sale in this tower?", "In Progress"),
	("kenji", "J-306", "Site Visit Request", "Is the studio available from the first of next month?", "Closed"),
]

SALE_LISTINGS = [
	dict(title="Marina Crest 2BR with Full Marina View - For Sale", unit="M-4001", price=2650000, featured=True,
	     desc="A bright corner two-bedroom on a high floor with a full marina view, a large balcony and two parking bays."),
	dict(title="Palm Meadows 4BR Family Villa - For Sale", unit="V-06", price=5150000, featured=False,
	     desc="A landscaped corner villa with a private garden and pool-ready terrace, in a gated family compound."),
	dict(title="Downtown Skyline Lofts 1BR Investor Unit - For Sale", unit="L-5E", price=1890000, featured=False,
	     desc="A furnished one-bedroom loft, offered as a ready-made rental investment in the heart of Downtown."),
]
