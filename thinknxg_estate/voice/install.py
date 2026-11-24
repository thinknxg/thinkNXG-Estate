import frappe

COMMANDS = [
    # (name, group, handler, needs_confirmation, keywords, phrases, entities)
    ("Create Lead", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.create_lead", 0,
     "create lead,new lead,add lead,add a lead",
     "create a new lead named Rahul\nadd lead for Priya number 9123456789",
     [("name", "Text", "full_name", 1), ("mobile", "Text", "mobile", 1),
      ("budget", "Money", "budget_max", 0), ("unit_type", "UnitType", "", 0)]),
    ("Update Lead", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.update_lead", 0,
     "update lead,update budget,change budget,budget is",
     "update the budget to 60 lakhs\nchange his budget",
     [("budget", "Money", "budget_max", 0), ("unit_type", "UnitType", "", 0),
      ("location", "Text", "preferred_location", 0)]),
    ("Add Note", "Capture", "thinknxg_estate.voice.commands.lead.add_note", 0,
     "add note,make a note,note this,voice note",
     "add a note to this lead\nnote this down", []),
    ("Qualify Lead", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.qualify_lead", 0,
     "qualify lead,mark qualified", "qualify this lead", []),
    ("Mark Won", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.mark_won", 1,
     "mark won,deal won,closed won", "mark this deal as won", []),
    ("Mark Lost", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.mark_lost", 1,
     "mark lost,deal lost,closed lost", "mark this deal as lost",
     [("reason", "Text", "lost_reason", 0)]),
    ("Close Lead", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.close_lead", 1,
     "close lead,disqualify", "close this lead", []),
    ("Assign to Agent", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.assign_agent", 1,
     "assign to,assign agent", "assign this to Sara",
     [("agent", "Text", "", 1)]),
    ("Transfer Lead", "Lead Lifecycle", "thinknxg_estate.voice.commands.lead.transfer_lead", 1,
     "transfer lead,transfer to", "transfer this lead to Ahmed",
     [("agent", "Text", "", 1)]),
    ("Book Visit", "Scheduling", "thinknxg_estate.voice.commands.scheduling.book_visit", 0,
     "book visit,schedule visit,site visit,arrange viewing",
     "book a site visit tomorrow at 4\nschedule a viewing on saturday morning",
     [("datetime", "DateTime", "visit_datetime", 1), ("unit", "Link", "unit", 0)]),
    ("Cancel Visit", "Scheduling", "thinknxg_estate.voice.commands.scheduling.cancel_visit", 1,
     "cancel visit,cancel viewing", "cancel the site visit", []),
    ("Schedule Reminder", "Scheduling",
     "thinknxg_estate.voice.commands.scheduling.schedule_reminder", 0,
     "remind me,set reminder,reminder", "remind me to call him tomorrow",
     [("datetime", "DateTime", "date", 0)]),
    ("Create Task", "Scheduling", "thinknxg_estate.voice.commands.scheduling.create_task", 0,
     "create task,add task,new task", "create a task to prepare the quotation",
     [("datetime", "DateTime", "date", 0)]),
    ("Search Property", "Query", "thinknxg_estate.voice.commands.queries.search_property", 0,
     "search property,find property,show properties,any properties,availability",
     "find a 2 BHK in Ruwi under 45 thousand\nshow me available villas",
     [("unit_type", "UnitType", "", 0), ("budget", "Money", "", 0),
      ("location", "Text", "", 0)]),
    ("Find Similar", "Query", "thinknxg_estate.voice.commands.queries.find_similar", 0,
     "find similar,similar properties,something similar",
     "find similar properties", []),
    ("Show Today's Follow-ups", "Query",
     "thinknxg_estate.voice.commands.queries.todays_followups", 0,
     "today follow ups,follow ups today,my follow ups,todays followups",
     "show me today's follow ups\nwhat are my follow ups", []),
    ("Show Pending Leads", "Query", "thinknxg_estate.voice.commands.queries.pending_leads", 0,
     "pending leads,open leads,my leads", "show my pending leads", []),
    ("Call Customer", "Comms", "thinknxg_estate.voice.commands.queries.call_customer", 0,
     "call customer,call him,call her,phone the customer",
     "call the customer", []),
    ("Send Brochure", "Content", "thinknxg_estate.voice.commands.content.send_brochure", 0,
     "send brochure,share brochure", "send the brochure", []),
    ("Send Price List", "Content", "thinknxg_estate.voice.commands.content.send_price_list", 0,
     "send price list,share price list,send prices", "send the price list", []),
    ("Share Location", "Content", "thinknxg_estate.voice.commands.content.share_location", 0,
     "share location,send location,send the map", "share the location", []),
    ("Generate Quotation", "Content",
     "thinknxg_estate.voice.commands.content.generate_quotation", 1,
     "generate quotation,make a quotation,create quote",
     "generate a quotation for this lead", []),
    ("Generate Booking Form", "Content",
     "thinknxg_estate.voice.commands.content.generate_booking_form", 1,
     "booking form,generate booking,create booking",
     "generate the booking form", []),
    ("Summarize Conversation", "Capture", "thinknxg_estate.voice.ai.insights.summarize_command", 0,
     "summarize,summary,recap", "summarize this lead\ngive me a recap", []),
]



def after_install():
    _seed_locale_profiles()
    _seed_commands()
    _seed_lead_source()


def _seed_locale_profiles():
    profiles = [
        ("GCC English/Arabic", 1, "en,ar,hi,ml", "International", "BR", "Asia/Muscat"),
        ("India Malayalam/English", 0, "en,ml,hi,ta", "Indian", "BHK",
         "Asia/Kolkata"),
    ]
    for name, default, languages, number_system, vocabulary, timezone in profiles:
        if frappe.db.exists("Voice Locale Profile", name):
            continue
        frappe.get_doc({
            "doctype": "Voice Locale Profile", "locale_name": name,
            "is_default": default, "languages": languages,
            "number_system": number_system, "unit_vocabulary": vocabulary,
            "timezone": timezone,
        }).insert(ignore_permissions=True)


def _seed_commands():
    for (name, group, handler, confirm, keywords, phrases, entities) in COMMANDS:
        if frappe.db.exists("Voice Command", name):
            continue
        command = frappe.new_doc("Voice Command")
        command.command_name = name
        command.command_group = group
        command.handler = handler
        command.needs_confirmation = confirm
        command.agent_only = 1
        command.enabled = 1
        command.keywords = keywords
        command.sample_phrases = phrases
        command.description = phrases.splitlines()[0] if phrases else name
        for entity_name, entity_type, target, required in entities:
            command.append("entities", {
                "entity_name": entity_name, "entity_type": entity_type,
                "target_field": target, "is_required": required})
        command.insert(ignore_permissions=True)


def _seed_lead_source():
    if frappe.db.exists("DocType", "Lead Source RE") and \
            not frappe.db.exists("Lead Source RE", "WhatsApp"):
        frappe.get_doc({"doctype": "Lead Source RE",
                        "source_name": "WhatsApp"}).insert(ignore_permissions=True)
