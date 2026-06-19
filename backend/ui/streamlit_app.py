import html
import uuid
from datetime import datetime

import requests
import streamlit as st

from config.settings import PUBLIC_BASE_URL

PUBLIC_BASE = PUBLIC_BASE_URL
RASA_WEBHOOK = f"{PUBLIC_BASE}/api/rasa/webhook"
HEALTH_RASA_URL = f"{PUBLIC_BASE}/api/health/rasa"
DIAG_URL = f"{PUBLIC_BASE}/api/diag"

st.set_page_config(
    page_title="NovaPlan.ai — Test Console",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .np-user-row {
        display: flex;
        justify-content: flex-end;
        margin: 0.25rem 0 0.6rem 0;
      }
      .np-bot-row {
        display: flex;
        justify-content: flex-start;
        margin: 0.25rem 0 0.6rem 0;
      }
      .np-user-text {
        max-width: 78%;
        color: #0F172A;
        text-align: right;
        line-height: 1.45;
        padding: 0.1rem 0;
      }
      .np-bot-text {
        max-width: 86%;
        color: #0F172A;
        text-align: left;
        line-height: 1.45;
        padding: 0.1rem 0;
      }
      div[data-testid="stChatInput"] {
        border: 1px solid #CBD5E1;
        border-radius: 14px;
        padding: 0.15rem;
        background: #FFFFFF;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
      }
      .np-summary-wrap {
        margin: 0.5rem 0 1rem 0;
      }
      .np-action-bar button {
        border-radius: 999px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session state init
for k, v in [
    ("messages",     []),
    ("sender_id",    f"test_{uuid.uuid4().hex[:8]}"),
    ("show_raw",     False),
    ("pending_send", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v


# Core functions
def rasa_health() -> dict:
    try:
        r = requests.get(HEALTH_RASA_URL, timeout=8)
        ct   = r.headers.get("content-type", "")
        data = r.json() if "application/json" in ct else {"status": r.text.strip()[:200]}
        return {"ok": r.status_code == 200, "data": data, "error": None}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "data": None,
                "error": "Rasa connection refused — still warming up. Wait ~60s then retry."}
    except requests.exceptions.Timeout:
        return {"ok": False, "data": None,
                "error": "Health check timed out — Rasa may still be loading the model."}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def send_to_rasa(text: str) -> list:
    try:
        r = requests.post(
            RASA_WEBHOOK,
            json={"sender": st.session_state.sender_id, "message": text},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.ConnectionError:
        return [{"text": "⚠️ Rasa is warming up — please try again in a moment."}]
    except requests.exceptions.Timeout:
        return [{"text": "⚠️ Rasa timed out. Your request may have been complex — try again."}]
    except Exception as e:
        return [{"text": f"⚠️ Error communicating with Rasa: {e}"}]


def _display_text_for_user_message(text: str) -> str:
    if text.startswith("/SetSlots"):
        return "Selected option"
    return text


def _clean_bot_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = text.strip()
    while cleaned.startswith("🤖"):
        cleaned = cleaned[1:].strip()
    return cleaned


def _render_user_bubble(text: str):
    st.markdown(
        f'<div class="np-user-row"><div class="np-user-text">{html.escape(str(text))}</div></div>',
        unsafe_allow_html=True,
    )


def _render_bot_bubble(text: str):
    cleaned = _clean_bot_text(text)
    if not cleaned:
        return
    # Use native markdown so bold, lists and tables render correctly.
    left, right = st.columns([0.86, 0.14])
    with left:
        st.markdown(cleaned)


def handle_send(text: str):
    if not text or not text.strip():
        return
    st.session_state.messages.append({"role": "user", "text": _display_text_for_user_message(text)})
    with st.spinner("NovaPlan is thinking…"):
        raw = send_to_rasa(text)
    st.session_state.messages.append({"role": "bot", "raw": raw})


# Rich response renderer
def render_bot_response(items: list, msg_idx: int):
    for item_idx, item in enumerate(items):
        prefix = f"msg{msg_idx}_item{item_idx}"

        if item.get("text"):
            has_summary_payload = any(
                (x.get("custom", {}) or {}).get("type") == "itinerary_summary"
                for x in items
            )
            text_value = _clean_bot_text(item.get("text", ""))
            if not (has_summary_payload and "Trip Summary" in text_value):
                _render_bot_bubble(text_value)

        custom    = item.get("custom", {})
        card_type = custom.get("type", "")
        data      = custom.get("data", {})

        def _format_travel_dates(dates_str: str) -> str:
            if not dates_str or not isinstance(dates_str, str):
                return dates_str
            s = dates_str.strip()
            # split common range separators
            for sep in (" to ", " - ", "–", "—"):
                if sep in s:
                    parts = [p.strip() for p in s.split(sep, 1)]
                    out = []
                    for p in parts:
                        try:
                            d = datetime.fromisoformat(p)
                            out.append(d.strftime("%d/%m/%Y"))
                        except Exception:
                            out.append(p)
                    return " to ".join(out)
            # try single ISO date
            try:
                d = datetime.fromisoformat(s)
                return d.strftime("%d/%m/%Y")
            except Exception:
                return s.title() if s.islower() else s

        # Carbon card
        if card_type == "carbon_card":
            icon = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(data.get("colour", ""), "⚪")
            with st.container(border=True):
                st.markdown(f"#### {icon} Carbon Footprint — {data.get('mode','').title()}")
                c1, c2, c3 = st.columns(3)
                c1.metric("CO₂e",   f"{data.get('kg_co2e', 0):.1f} kg")
                c2.metric("Mode",   data.get("mode", "—").title())
                c3.metric("Impact", data.get("colour", "—").capitalize())
                st.caption(f"Source: {data.get('source','estimate')} | {data.get('disclaimer','')}")

        # Transport options
        elif card_type == "transport_options":
            with st.container(border=True):
                st.markdown(f"#### 🚆 {data.get('origin','?')} → {data.get('destination','?')}")
                for opt in data.get("options", []):
                    eco = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(opt.get("eco_rating",""), "⚪")
                    with st.expander(f"{eco} {opt.get('mode','?').title()} — {opt.get('duration','?')} · {opt.get('cost','?')}"):
                        st.write(opt.get("details", "No details available"))
                        st.metric("Emissions", f"{opt.get('emissions', 0):.1f} kg CO₂e")

        # Hotel carousel
        elif card_type == "hotel_carousel":
            hotels = data.get("hotels", [])
            with st.container(border=True):
                st.markdown(f"#### 🏨 Eco Hotels in {data.get('destination','?')}")
                if hotels:
                    cols = st.columns(min(3, len(hotels)))
                    for i, h in enumerate(hotels):
                        with cols[i % 3]:
                            st.markdown(f"**{h.get('name','?')}** {'🌿' if h.get('eco_badge') else ''}")
                            st.write(f"⭐ {h.get('rating','?')} | {h.get('price','?')}")
                            st.caption(h.get("description",""))
                else:
                    st.info("No hotels found for this destination/budget.")

        # Cultural tips
        elif card_type == "cultural_tips":
            with st.container(border=True):
                st.markdown(f"#### 🌍 {data.get('destination','?')} — Cultural Tips")
                st.write(f"Sustainability rating: **{data.get('sustainability_rating','N/A')}**")
                for cat, info in data.get("data", {}).items():
                    with st.expander(f"📌 {info.get('category', cat)}"):
                        for tip in info.get("tips", []):
                            st.markdown(f"• {tip}")

        # Itinerary summary
        elif card_type == "itinerary_summary":
            st.markdown('<div class="np-summary-wrap">', unsafe_allow_html=True)
            with st.container(border=True):
                booking = data.get("booking", {}) or {}
                destination_name = booking.get("destination") or data.get("destination") or "Destination"
                origin_name = booking.get("origin") or data.get("origin") or "Origin"
                travel_dates = _format_travel_dates(booking.get("travel_dates") or data.get("travel_dates"))
                travellers = booking.get("num_travellers", data.get("num_travellers", "—"))
                budget = booking.get("budget_eur", data.get("budget_eur", "—"))
                eco_level = str(booking.get("eco_level", data.get("eco_level", "—"))).title()
                transport_mode = str(booking.get("transport_mode", data.get("transport_mode", "—"))).title()

                st.markdown("## Trip Summary")
                st.caption(f"{origin_name} → {destination_name}")

                st.markdown("### About Booking and Destination")
                dest_info = data.get("destination_info") or {}
                if isinstance(dest_info, dict):
                    wiki_html = dest_info.get("wiki_html") or dest_info.get("extract_html") or dest_info.get("description")
                    facts = dest_info.get("facts") or dest_info.get("country_overview") or []
                else:
                    wiki_html = data.get("destination_description") or str(dest_info or "")
                    facts = []

                with st.container(border=True):
                    st.markdown(f"#### About {destination_name}")
                    st.markdown(wiki_html or "Destination information is unavailable.", unsafe_allow_html=True)

                col_booking, col_destination = st.columns(2)
                with col_booking:
                    st.markdown("#### Booking Summary")
                    st.table([
                        {"Field": "Route", "Details": f"{origin_name} → {destination_name}"},
                        {"Field": "Dates", "Details": travel_dates or "—"},
                        {"Field": "Travellers", "Details": travellers},
                        {"Field": "Budget", "Details": f"€{budget}"},
                        {"Field": "Eco preference", "Details": eco_level},
                        {"Field": "Transport", "Details": transport_mode},
                    ])
                with col_destination:
                    st.markdown("#### More about Destination")
                    if facts:
                        fact_rows = []
                        for fact in facts:
                            if isinstance(fact, dict):
                                fact_rows.append({"Field": fact.get("field", "Info"), "Details": fact.get("value", "—")})
                            else:
                                text = str(fact)
                                if ":" in text:
                                    field, value = text.split(":", 1)
                                    fact_rows.append({"Field": field.strip(), "Details": value.strip()})
                                else:
                                    fact_rows.append({"Field": "Info", "Details": text})
                        st.table(fact_rows)
                    else:
                        st.info("Additional destination details are unavailable.")

                st.markdown("### Ticket Options")
                transport_options = (data.get("transport_options", []) or [])[:1]
                if transport_options:
                    opt = transport_options[0]
                    with st.container(border=True):
                        st.markdown(f"#### {str(opt.get('mode', 'Flight')).title()} Option")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Price / traveller", opt.get("cost", "—"))
                        c2.metric("Duration", opt.get("duration", "—"))
                        c3.metric("CO₂e", f"{float(opt.get('emissions', 0)):.1f} kg" if opt.get("emissions") is not None else "—")
                        st.markdown(f"**Airline/Operator:** {opt.get('airline') or '—'}")
                        st.markdown(f"**Outbound:** {opt.get('departure') or '—'}")
                        st.markdown(f"**Return:** {opt.get('return') or '—'}")
                        if opt.get("details"):
                            st.caption(str(opt.get("details")).replace("\n", "  \n"))
                else:
                    st.info("Ticket search completed, but no matching options were returned.")

                st.markdown("### Hotel Options")
                hotel_options = (data.get("hotel_options", []) or [])[:1]
                if hotel_options:
                    h = hotel_options[0]
                    amenities = h.get("amenities") or []
                    with st.container(border=True):
                        st.markdown(f"#### {h.get('name', 'Eco hotel')}")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Price / night", h.get("price", "—"))
                        c2.metric("Rating", h.get("rating", "—"))
                        c3.metric("Hotel CO₂/night", f"{h.get('carbon_kg', '—')} kg")
                        st.markdown(f"**Area/Address:** {h.get('address') or '—'}")
                        st.markdown(f"**Sustainability:** {h.get('description', 'Eco-friendly property')}")
                        st.caption("Highlights: " + (", ".join(amenities) if isinstance(amenities, list) else str(amenities or "—")))
                else:
                    st.info("No eco-hotel options are available for this summary.")

                st.markdown("### Carbon Footprint")
                carbon = data.get("carbon", {}) or {}
                carbon_val = carbon.get("kg_co2e", data.get("carbon_kg"))
                try:
                    carbon_display = f"{float(carbon_val):.1f} kg CO₂e"
                except Exception:
                    carbon_display = "—"
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    c1.metric("Estimated journey emissions", carbon_display)
                    c2.markdown("Carbon values are estimates and depend on route, vehicle type, load factor, and source data availability.")

                st.markdown("### Trip Price")
                trip_price = data.get("trip_price") or {}
                if trip_price:
                    num_people = trip_price.get('num_travellers', travellers)
                    nights = trip_price.get('nights', 1)
                    ticket_each = float(trip_price.get('ticket_price_per_traveller', 0) or 0)
                    hotel_each = float(trip_price.get('hotel_price_per_night', 0) or 0)
                    ticket_total = float(trip_price.get('ticket_total', 0) or 0)
                    hotel_total = float(trip_price.get('hotel_total', 0) or 0)
                    grand_total = float(trip_price.get('total', data.get('price_total', 0)) or 0)
                    st.table([
                        {
                            "Cost item": "Tickets",
                            "Calculation": f"Each ticket price €{ticket_each:.2f} and for {num_people} traveller(s)",
                            "Amount": f"€{ticket_total:.2f}",
                        },
                        {
                            "Cost item": "Hotel",
                            "Calculation": f"Per night stay is €{hotel_each:.2f} and for {nights} night(s) for {num_people} person(s)",
                            "Amount": f"€{hotel_total:.2f}",
                        },
                        {
                            "Cost item": "Total",
                            "Calculation": "Tickets + hotel",
                            "Amount": f"€{grand_total:.2f}",
                        },
                    ])
                else:
                    st.info("Trip price is unavailable because ticket or hotel pricing was missing.")

                st.info("Please choose an option below: Confirm Trip, Modify Trip, Cancel Trip, or Start Again.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Escalation banner
        elif card_type == "escalation_banner":
            st.warning(
                f"🚨 **Human handover** | "
                f"Ticket: `{data.get('ticket_id','?')}` | "
                f"Severity: {data.get('severity','?')}",
                icon="🚨",
            )

        # Quick reply buttons
        elif card_type == "quick_reply":
            replies = data.get("replies", [])
            if replies:
                st.markdown("**Suggested replies:**")
                cols = st.columns(min(len(replies), 3))
                for i, reply in enumerate(replies):
                    if isinstance(reply, dict):
                        title = reply.get("title", "Option")
                        payload = reply.get("payload", title)
                    else:
                        title = str(reply)
                        payload = title

                    if cols[i % 3].button(title, key=f"{prefix}_qr{i}"):
                        st.session_state.pending_send = payload

        # Native Rasa buttons
        if item.get("buttons"):
            st.markdown("**Options:**")
            btns = item["buttons"]
            cols = st.columns(min(len(btns), 3))
            for i, btn in enumerate(btns):
                label   = btn.get("title",   f"Option {i+1}")
                payload = btn.get("payload", label)
                send_text = payload
                if cols[i % 3].button(label, key=f"{prefix}_btn{i}"):
                    st.session_state.pending_send = send_text

        if st.session_state.show_raw:
            with st.expander("Raw JSON"):
                st.json(item)


# Sidebar
with st.sidebar:
    st.title("🤖 NovaPlan.ai")
    st.caption(f"Session: `{st.session_state.sender_id}`")

    # Health check
    with st.expander("🔌 Backend Health", expanded=True):
        if st.button("Check Rasa", key="health_btn"):
            with st.spinner("Pinging Rasa…"):
                h = rasa_health()
            if h["ok"]:
                st.success("✅ Rasa is up and running")
                st.json(h["data"])
            else:
                # h["error"] is always set when ok=False
                st.error(f"❌ {h['error']}")

    st.divider()

    # API status panel — calls /api/diag for live server-side status
    with st.expander("🔑 API & Diagnostics"):
        if st.button("Run diagnostics", key="diag_btn"):
            try:
                r = requests.get(DIAG_URL, timeout=15)
                diag = r.json()

                st.markdown("**Environment Variables (server-side):**")
                for k, v in diag.get("env_vars", {}).items():
                    if "NOT SET" in str(v):
                        st.warning(f"⚠️ {k}: {v}")
                    else:
                        st.success(f"✅ {k}: {v}")

                st.markdown("**Health checks:**")
                health = diag.get("health", {})
                st.json(health)
                st.write(
                    "Mock mode:",
                    "🔴 ON (real APIs disabled)" if diag.get("mock_mode") else "🟢 OFF (real APIs active)",
                )

            except Exception as e:
                st.error(f"Diagnostics failed: {e}")

    st.divider()

    # Quick intent test buttons
    st.markdown("**Quick Tests**")
    tests = {
        "👋 Hello":              "Hello",
        "✈️ Plan a trip":        "I want to plan an eco-friendly trip to Amsterdam from Berlin",
        "🌍 Carbon footprint":   "What is the carbon footprint of flying from London to Berlin?",
        "🚆 Transport options":  "Show me transport options from Berlin to Paris",
        "🏨 Eco hotels":         "Find eco hotels in Amsterdam under 1000 euros",
        "🌱 Offset programs":    "How can I offset my carbon footprint?",
        "🗺️ Cultural tips":      "Give me cultural tips for Japan",
        "🆘 Speak to human":     "I need to speak to a human agent",
        "🔄 Start over":         "Restart",
        "🤖 Bot challenge":      "Are you a bot?",
        "👋 Goodbye":            "Goodbye",
    }
    for label, payload in tests.items():
        if st.button(label, use_container_width=True, key=f"test_{label}"):
            handle_send(payload)
            st.rerun()

    st.divider()
    st.session_state.show_raw = st.toggle("🔍 Show raw JSON", value=st.session_state.show_raw)

    if st.button("🗑️ Reset conversation", use_container_width=True):
        st.session_state.messages     = []
        st.session_state.sender_id    = f"test_{uuid.uuid4().hex[:8]}"
        st.session_state.pending_send = None
        st.rerun()

    st.divider()
    st.caption(f"API base: {PUBLIC_BASE}")
    st.caption("Chat via /api/rasa/webhook (through nginx)")


# Main chat area
st.title("Test Console")
st.caption("Test Rasa chatbot here. With quick-reply buttons continue the conversation automatically.")

# Render all messages — use enumerate for stable button keys
for msg_idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        _render_user_bubble(msg["text"])
    else:
        if msg.get("raw"):
            render_bot_response(msg["raw"], msg_idx)

# Process pending button click AFTER rendering (preserves message order)
if st.session_state.pending_send:
    msg = st.session_state.pending_send
    st.session_state.pending_send = None
    handle_send(msg)
    st.rerun()

# Free text input
if prompt := st.chat_input("Type your message here…"):
    handle_send(prompt)
    st.rerun()
