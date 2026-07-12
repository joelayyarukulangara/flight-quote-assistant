"""
Optional LLM-powered customer quote wording.

Works with ANY LLM provider that exposes an OpenAI-compatible chat
completions endpoint -- which is nearly all of them (OpenAI, Groq,
Mistral, DeepSeek, OpenRouter, Together, Gemini, local Ollama, ...).
The base URL and model name come from Settings, so switching providers
is just: paste key, set base URL, set model name.

IMPORTANT: This service NEVER fetches flight fares. Fares always come from
the flight provider (SerpAPI / SearchAPI / mock). The LLM is used only
after rule-based filtering and ranking are complete, to turn the
already-selected best 4 package combinations into clean customer-facing
wording.

If no API key is configured, AI summary is disabled and callers should use
the rule-based fallback template produced by build_rule_based_summary().
The app must work fully without any LLM.
"""
import json

from config import FARE_WARNING_TEXT
from utils.date_utils import now_str

try:
    from openai import OpenAI
except ImportError:  # openai package optional; app must still run without it
    OpenAI = None


class AiSummaryError(Exception):
    pass


def _compact_payload(quote_result, customer_info, package_info):
    """Build a compact JSON-able summary of only the best 4 options, to
    minimize tokens and avoid ever sending raw search results."""
    options = []
    for combo in quote_result.combinations:
        up, down = combo.up_flight, combo.down_flight
        options.append(
            {
                "category": combo.category,
                "package": f"{combo.package_days}D/{combo.package_nights}N",
                "up": {
                    "route": f"{up.origin}-{up.destination}",
                    "date": up.departure_datetime.strftime("%d %b %Y"),
                    "airline": up.airline,
                    "stops": up.stops,
                },
                "down": {
                    "route": f"{down.origin}-{down.destination}",
                    "date": down.departure_datetime.strftime("%d %b %Y"),
                    "airline": down.airline,
                    "stops": down.stops,
                },
                "fare_per_person": combo.final_quote_per_person,
                "currency": quote_result.request.currency,
                "warnings": combo.warnings,
            }
        )
    return {
        "customer": customer_info,
        "package": package_info,
        "options": options,
    }


def build_rule_based_summary(quote_result, customer_info, package_info, language="English"):
    """Deterministic, no-AI fallback quote text. Always available."""
    lines = [f"{package_info.get('name', 'Tour Package')} - Flight Options", ""]
    lines.append(f"Customer: {customer_info.get('name', '')}")
    lines.append(f"Package: {package_info.get('name', '')}")
    lines.append("")
    for i, combo in enumerate(quote_result.combinations, start=1):
        up, down = combo.up_flight, combo.down_flight
        lines.append(f"Option {i}: {combo.category}")
        lines.append(f"UP: {up.origin} to {up.destination}, {up.departure_datetime.strftime('%d %b')}, {up.airline}")
        lines.append(f"DOWN: {down.origin} to {down.destination}, {down.departure_datetime.strftime('%d %b')}, {down.airline}")
        lines.append(f"Fare: {quote_result.request.currency} {combo.final_quote_per_person:,.0f} per person")
        if combo.warnings:
            lines.append("Note: " + "; ".join(combo.warnings) + " (to be verified before ticketing)")
        lines.append("")
    lines.append(f"Fare checked on: {now_str()}")
    lines.append(FARE_WARNING_TEXT.format(timestamp=now_str()))
    return "\n".join(lines)


def generate_customer_quote_summary(quote_result, customer_info, package_info, api_key,
                                     model="gpt-4o-mini", language="English",
                                     base_url="https://api.openai.com/v1"):
    """Generate customer-friendly quote wording using any OpenAI-compatible LLM.

    Only called when the user explicitly clicks "Generate AI Quote". Falls
    back to the rule-based template on any failure (missing key, package
    missing, network error, bad response).
    """
    if not api_key or OpenAI is None:
        text = build_rule_based_summary(quote_result, customer_info, package_info, language)
        return text, "AI summary unavailable; standard quote generated."

    payload = _compact_payload(quote_result, customer_info, package_info)
    fare_warning = FARE_WARNING_TEXT.format(timestamp=now_str())

    system_prompt = (
        "You write short, professional customer-facing flight quote messages for a travel "
        "agency. Use ONLY the data given in the JSON payload -- never invent prices, baggage, "
        "refund rules, or airline details. Do not mention API sources, internal scores, or "
        "any technical details. If baggage or refund info is uncertain, say it will be "
        "verified before ticketing. Always end with this exact fare warning line: "
        f"\"{fare_warning}\". Write the message in {language}. Keep it concise and ready to "
        "send to a customer via WhatsApp or PDF."
    )

    try:
        client = OpenAI(api_key=api_key, base_url=base_url or "https://api.openai.com/v1")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
            temperature=0.4,
        )
        text = response.choices[0].message.content.strip()
        if not text:
            raise AiSummaryError("Empty response from OpenAI")
        return text, None
    except Exception:
        text = build_rule_based_summary(quote_result, customer_info, package_info, language)
        return text, "AI summary unavailable; standard quote generated."
