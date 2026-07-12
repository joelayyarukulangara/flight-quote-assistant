"""Settings tab."""
from tkinter import messagebox

import customtkinter as ctk

import database
from config import (
    CURRENCIES, MARKUP_TYPES, MAX_STOPS_OPTIONS, MAX_LAYOVER_OPTIONS, MIN_LAYOVER_OPTIONS,
    BAGGAGE_OPTIONS, RETURN_CALC_RULES, AI_LANGUAGES, FLIGHT_PROVIDERS, AI_BASE_URL_PRESETS,
)


class SettingsView(ctk.CTkScrollableFrame):
    def __init__(self, parent):
        super().__init__(parent, label_text="Settings")
        self.grid_columnconfigure(0, weight=1)
        self._build_form()
        self._load_settings()

    def _build_form(self):
        api_frame = ctk.CTkFrame(self, corner_radius=8)
        api_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        api_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(api_frame, text="FLIGHT DATA PROVIDER", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5)
        )

        ctk.CTkLabel(api_frame, text="Flight data source").grid(row=1, column=0, sticky="w", padx=10)
        self.flight_provider_menu = ctk.CTkOptionMenu(api_frame, values=FLIGHT_PROVIDERS)
        self.flight_provider_menu.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(api_frame, text="SerpAPI API key (used when SerpAPI is selected)").grid(row=3, column=0, sticky="w", padx=10)
        self.serpapi_key_entry = ctk.CTkEntry(api_frame, show="*")
        self.serpapi_key_entry.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(api_frame, text="SearchAPI API key (used when SearchAPI is selected)").grid(row=5, column=0, sticky="w", padx=10)
        self.searchapi_key_entry = ctk.CTkEntry(api_frame, show="*")
        self.searchapi_key_entry.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            api_frame,
            text="If the selected provider's key is missing, the app uses mock sample data and shows a warning.",
            text_color="gray",
        ).grid(row=7, column=0, sticky="w", padx=10, pady=(0, 10))

        defaults_frame = ctk.CTkFrame(self, corner_radius=8)
        defaults_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        for i in range(2):
            defaults_frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(defaults_frame, text="DEFAULTS", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5)
        )

        ctk.CTkLabel(defaults_frame, text="Company name (shown on quotes)").grid(row=1, column=0, sticky="w", padx=10)
        self.company_name_entry = ctk.CTkEntry(defaults_frame)
        self.company_name_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Default currency").grid(row=1, column=1, sticky="w", padx=10)
        self.default_currency_menu = ctk.CTkOptionMenu(defaults_frame, values=CURRENCIES)
        self.default_currency_menu.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Default markup type").grid(row=3, column=0, sticky="w", padx=10)
        self.default_markup_type_menu = ctk.CTkOptionMenu(defaults_frame, values=MARKUP_TYPES)
        self.default_markup_type_menu.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Default markup value").grid(row=3, column=1, sticky="w", padx=10)
        self.default_markup_value_entry = ctk.CTkEntry(defaults_frame)
        self.default_markup_value_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Cache duration (minutes)").grid(row=5, column=0, sticky="w", padx=10)
        self.cache_duration_entry = ctk.CTkEntry(defaults_frame)
        self.cache_duration_entry.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Default max stops").grid(row=7, column=0, sticky="w", padx=10)
        self.default_max_stops_menu = ctk.CTkOptionMenu(defaults_frame, values=list(MAX_STOPS_OPTIONS.keys()))
        self.default_max_stops_menu.grid(row=8, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Default max layover").grid(row=7, column=1, sticky="w", padx=10)
        self.default_max_layover_menu = ctk.CTkOptionMenu(defaults_frame, values=list(MAX_LAYOVER_OPTIONS.keys()))
        self.default_max_layover_menu.grid(row=8, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Default minimum layover").grid(row=9, column=0, sticky="w", padx=10)
        self.default_min_layover_menu = ctk.CTkOptionMenu(defaults_frame, values=list(MIN_LAYOVER_OPTIONS.keys()))
        self.default_min_layover_menu.grid(row=10, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Default baggage requirement").grid(row=9, column=1, sticky="w", padx=10)
        self.default_baggage_menu = ctk.CTkOptionMenu(defaults_frame, values=BAGGAGE_OPTIONS)
        self.default_baggage_menu.grid(row=10, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(defaults_frame, text="Return date calculation rule").grid(row=11, column=0, sticky="w", padx=10)
        self.return_calc_rule_menu = ctk.CTkOptionMenu(defaults_frame, values=RETURN_CALC_RULES)
        self.return_calc_rule_menu.grid(row=12, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))

        ai_frame = ctk.CTkFrame(self, corner_radius=8)
        ai_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        for i in range(2):
            ai_frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(ai_frame, text="AI QUOTE WORDING (OPTIONAL)", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5)
        )

        self.enable_ai_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ai_frame, text="Enable AI summary (requires an LLM API key below)",
                        variable=self.enable_ai_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

        ctk.CTkLabel(ai_frame, text="LLM API key").grid(row=2, column=0, sticky="w", padx=10)
        self.openai_key_entry = ctk.CTkEntry(ai_frame, show="*")
        self.openai_key_entry.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(ai_frame, text="Provider preset (fills base URL)").grid(row=2, column=1, sticky="w", padx=10)
        self.ai_preset_menu = ctk.CTkOptionMenu(
            ai_frame, values=list(AI_BASE_URL_PRESETS.keys()), command=self._on_ai_preset_change
        )
        self.ai_preset_menu.grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(ai_frame, text="API base URL (any OpenAI-compatible endpoint)").grid(row=4, column=0, sticky="w", padx=10)
        self.ai_base_url_entry = ctk.CTkEntry(ai_frame)
        self.ai_base_url_entry.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(ai_frame, text="Model name (e.g. gpt-4o-mini, llama-3.3-70b-versatile)").grid(row=4, column=1, sticky="w", padx=10)
        self.ai_model_name_entry = ctk.CTkEntry(ai_frame)
        self.ai_model_name_entry.grid(row=5, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(ai_frame, text="AI language").grid(row=6, column=0, sticky="w", padx=10)
        self.ai_language_menu = ctk.CTkOptionMenu(ai_frame, values=AI_LANGUAGES)
        self.ai_language_menu.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 8))

        note = ctk.CTkLabel(
            ai_frame,
            text="Works with any LLM provider exposing an OpenAI-compatible endpoint: OpenAI, Groq,\n"
                 "Mistral, DeepSeek, OpenRouter, Gemini, local Ollama, etc. Pick a preset or paste a base URL,\n"
                 "then enter that provider's key and one of its model names.\n"
                 "AI is used only for customer-facing wording after search results are ready --\n"
                 "it never fetches or invents flight fares. If no key is set, a rule-based quote is used instead.",
            text_color="gray", justify="left", wraplength=680,
        )
        note.grid(row=8, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        ctk.CTkButton(self, text="Save Settings", command=self._save).grid(row=3, column=0, sticky="ew", padx=10, pady=20)

    def _on_ai_preset_change(self, preset_name):
        url = AI_BASE_URL_PRESETS.get(preset_name)
        if url:
            self.ai_base_url_entry.delete(0, "end")
            self.ai_base_url_entry.insert(0, url)

    def _load_settings(self):
        settings = database.get_all_settings()

        def set_entry(entry, key):
            entry.delete(0, "end")
            entry.insert(0, settings.get(key, ""))

        self.flight_provider_menu.set(settings.get("flight_provider", "Mock (sample data)"))
        set_entry(self.serpapi_key_entry, "serpapi_api_key")
        set_entry(self.searchapi_key_entry, "searchapi_api_key")
        set_entry(self.openai_key_entry, "openai_api_key")
        set_entry(self.ai_base_url_entry, "ai_base_url")
        set_entry(self.ai_model_name_entry, "ai_model_name")

        set_entry(self.company_name_entry, "company_name")
        self.default_currency_menu.set(settings.get("default_currency", "INR"))
        self.default_markup_type_menu.set(settings.get("default_markup_type", "No markup"))
        set_entry(self.default_markup_value_entry, "default_markup_value")
        set_entry(self.cache_duration_entry, "cache_duration_minutes")
        self.default_max_stops_menu.set(settings.get("default_max_stops", "Max 1 stop"))
        self.default_max_layover_menu.set(settings.get("default_max_layover", "6 hours"))
        self.default_min_layover_menu.set(settings.get("default_min_layover", "1 hour 15 minutes"))
        self.default_baggage_menu.set(settings.get("default_baggage", "Checked baggage required"))
        self.return_calc_rule_menu.set(settings.get("return_calc_rule", RETURN_CALC_RULES[0]))

        self.enable_ai_var.set(settings.get("enable_ai_summary", "false") == "true")
        self.ai_language_menu.set(settings.get("ai_language", "English"))

    def _save(self):
        openai_key = self.openai_key_entry.get().strip()
        enable_ai = self.enable_ai_var.get() and bool(openai_key)
        if self.enable_ai_var.get() and not openai_key:
            messagebox.showwarning("AI summary disabled", "LLM API key is missing; AI summary will stay disabled.")

        provider_choice = self.flight_provider_menu.get()
        if provider_choice.startswith("SerpAPI") and not self.serpapi_key_entry.get().strip():
            messagebox.showwarning(
                "No SerpAPI key",
                "SerpAPI is selected but no SerpAPI key is entered -- searches will use mock data until a key is added.",
            )
        if provider_choice.startswith("SearchAPI") and not self.searchapi_key_entry.get().strip():
            messagebox.showwarning(
                "No SearchAPI key",
                "SearchAPI is selected but no SearchAPI key is entered -- searches will use mock data until a key is added.",
            )

        values = {
            "flight_provider": provider_choice,
            "serpapi_api_key": self.serpapi_key_entry.get().strip(),
            "searchapi_api_key": self.searchapi_key_entry.get().strip(),
            "openai_api_key": openai_key,
            "ai_base_url": self.ai_base_url_entry.get().strip() or "https://api.openai.com/v1",
            "ai_model_name": self.ai_model_name_entry.get().strip() or "gpt-4o-mini",
            "company_name": self.company_name_entry.get().strip() or "Your Travel Company",
            "default_currency": self.default_currency_menu.get(),
            "default_markup_type": self.default_markup_type_menu.get(),
            "default_markup_value": self.default_markup_value_entry.get().strip() or "0",
            "cache_duration_minutes": self.cache_duration_entry.get().strip() or "60",
            "default_max_stops": self.default_max_stops_menu.get(),
            "default_max_layover": self.default_max_layover_menu.get(),
            "default_min_layover": self.default_min_layover_menu.get(),
            "default_baggage": self.default_baggage_menu.get(),
            "return_calc_rule": self.return_calc_rule_menu.get(),
            "enable_ai_summary": "true" if enable_ai else "false",
            "ai_language": self.ai_language_menu.get(),
        }
        database.set_settings(values)
        messagebox.showinfo("Saved", "Settings saved.")
