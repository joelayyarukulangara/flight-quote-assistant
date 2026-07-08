"""New Quote tab: the main data-entry form."""
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox

from config import (
    CURRENCIES, TRAVEL_CLASSES, TIME_PREFERENCES, DURATION_PRESETS,
    RETURN_FLEX_OPTIONS, MAX_STOPS_OPTIONS, MAX_LAYOVER_OPTIONS, MIN_LAYOVER_OPTIONS,
    BAGGAGE_OPTIONS, SORT_PREFERENCES, MARKUP_TYPES, ROUNDING_OPTIONS, RETURN_CALC_RULES,
    API_CALL_WARNING_THRESHOLD,
)
from models import (
    PassengerInfo, RouteQuery, PackageDuration, SearchFilters, FlightSearchRequest,
)
from utils.airport_utils import normalize_airport_input
from services.date_pair_service import generate_date_pairs, estimate_search_cost


def _parse_date(text, field_label):
    text = text.strip()
    if not text:
        raise ValueError(f"{field_label} is required (format YYYY-MM-DD).")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{field_label} must be in YYYY-MM-DD format.")


class RouteSection(ctk.CTkFrame):
    def __init__(self, parent, title):
        super().__init__(parent, corner_radius=8)
        self.title = title

        header = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=15, weight="bold"))
        header.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(self, text="From (city or code)").grid(row=1, column=0, sticky="w", padx=10)
        self.from_entry = ctk.CTkEntry(self, placeholder_text="e.g. Kochi or COK")
        self.from_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text="To (city or code)").grid(row=1, column=1, sticky="w", padx=10)
        self.to_entry = ctk.CTkEntry(self, placeholder_text="e.g. Dubai or DXB")
        self.to_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text="Departure date from (YYYY-MM-DD)").grid(row=1, column=2, sticky="w", padx=10)
        self.date_from_entry = ctk.CTkEntry(self, placeholder_text="2026-08-10")
        self.date_from_entry.grid(row=2, column=2, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text="Departure date to (YYYY-MM-DD)").grid(row=1, column=3, sticky="w", padx=10)
        self.date_to_entry = ctk.CTkEntry(self, placeholder_text="2026-08-15")
        self.date_to_entry.grid(row=2, column=3, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text="Preferred departure time").grid(row=3, column=0, sticky="w", padx=10)
        self.dep_time_menu = ctk.CTkOptionMenu(self, values=TIME_PREFERENCES)
        self.dep_time_menu.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text="Preferred arrival time").grid(row=3, column=1, sticky="w", padx=10)
        self.arr_time_menu = ctk.CTkOptionMenu(self, values=TIME_PREFERENCES)
        self.arr_time_menu.grid(row=4, column=1, sticky="ew", padx=10, pady=(0, 8))

        self.nearby_origin_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self, text="Allow nearby origin airports", variable=self.nearby_origin_var).grid(
            row=4, column=2, sticky="w", padx=10, pady=(0, 8)
        )
        self.nearby_dest_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self, text="Allow nearby destination airports", variable=self.nearby_dest_var).grid(
            row=4, column=3, sticky="w", padx=10, pady=(0, 8)
        )

        for i in range(4):
            self.grid_columnconfigure(i, weight=1)

    def to_route_query(self, label):
        origin = normalize_airport_input(self.from_entry.get())
        destination = normalize_airport_input(self.to_entry.get())
        if not origin or not destination:
            raise ValueError(f"{label}: From and To fields are required.")
        date_from = _parse_date(self.date_from_entry.get(), f"{label} departure date from")
        date_to = _parse_date(self.date_to_entry.get(), f"{label} departure date to")
        if date_from > date_to:
            raise ValueError(f"{label}: departure date range is invalid (from is after to).")
        return RouteQuery(
            origin=origin, destination=destination, date_from=date_from, date_to=date_to,
            preferred_departure_time=self.dep_time_menu.get(),
            preferred_arrival_time=self.arr_time_menu.get(),
            allow_nearby_origin=self.nearby_origin_var.get(),
            allow_nearby_destination=self.nearby_dest_var.get(),
        )


class SearchForm(ctk.CTkScrollableFrame):
    def __init__(self, parent, on_search):
        super().__init__(parent, label_text="New Quote")
        self.on_search = on_search
        self.grid_columnconfigure(0, weight=1)

        self._build_general_section()
        self._build_route_sections()
        self._build_duration_section()
        self._build_filters_section()
        self._build_commercials_section()

        self.search_button = ctk.CTkButton(self, text="Estimate & Search", command=self._handle_search)
        self.search_button.grid(row=99, column=0, sticky="ew", padx=10, pady=20)

    # -------------------------------------------------------------- general
    def _build_general_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        for i in range(4):
            frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(frame, text="GENERAL", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5)
        )

        ctk.CTkLabel(frame, text="Customer / Group Name").grid(row=1, column=0, sticky="w", padx=10)
        self.customer_entry = ctk.CTkEntry(frame)
        self.customer_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Package Name").grid(row=1, column=1, sticky="w", padx=10)
        self.package_entry = ctk.CTkEntry(frame)
        self.package_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Adults").grid(row=1, column=2, sticky="w", padx=10)
        self.adults_entry = ctk.CTkEntry(frame)
        self.adults_entry.insert(0, "2")
        self.adults_entry.grid(row=2, column=2, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Children").grid(row=1, column=3, sticky="w", padx=10)
        self.children_entry = ctk.CTkEntry(frame)
        self.children_entry.insert(0, "0")
        self.children_entry.grid(row=2, column=3, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Infants").grid(row=3, column=0, sticky="w", padx=10)
        self.infants_entry = ctk.CTkEntry(frame)
        self.infants_entry.insert(0, "0")
        self.infants_entry.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Travel Class").grid(row=3, column=1, sticky="w", padx=10)
        self.travel_class_menu = ctk.CTkOptionMenu(frame, values=TRAVEL_CLASSES)
        self.travel_class_menu.grid(row=4, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Currency").grid(row=3, column=2, sticky="w", padx=10)
        self.currency_menu = ctk.CTkOptionMenu(frame, values=CURRENCIES)
        self.currency_menu.grid(row=4, column=2, sticky="ew", padx=10, pady=(0, 8))

    # -------------------------------------------------------------- routes
    def _build_route_sections(self):
        self.up_section = RouteSection(self, "UP / ONWARD FLIGHT")
        self.up_section.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        reverse_btn = ctk.CTkButton(self, text="Reverse Up Route → Fill Down Route", command=self._reverse_route)
        reverse_btn.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

        self.down_section = RouteSection(self, "DOWN / RETURN FLIGHT")
        self.down_section.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

    def _reverse_route(self):
        self.down_section.from_entry.delete(0, "end")
        self.down_section.from_entry.insert(0, self.up_section.to_entry.get())
        self.down_section.to_entry.delete(0, "end")
        self.down_section.to_entry.insert(0, self.up_section.from_entry.get())

    # ------------------------------------------------------------ duration
    def _build_duration_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        for i in range(4):
            frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(frame, text="PACKAGE DURATION", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5)
        )

        ctk.CTkLabel(frame, text="Duration mode").grid(row=1, column=0, sticky="w", padx=10)
        self.duration_mode_menu = ctk.CTkOptionMenu(
            frame, values=["Fixed package duration", "Custom date gap", "Manual return date range"],
            command=self._on_duration_mode_change,
        )
        self.duration_mode_menu.set("Fixed package duration")
        self.duration_mode_menu.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Package length").grid(row=1, column=1, sticky="w", padx=10)
        self.duration_preset_menu = ctk.CTkOptionMenu(
            frame, values=[p[0] for p in DURATION_PRESETS], command=self._on_preset_change,
        )
        self.duration_preset_menu.set("4 Days / 3 Nights")
        self.duration_preset_menu.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Custom days").grid(row=1, column=2, sticky="w", padx=10)
        self.custom_days_entry = ctk.CTkEntry(frame)
        self.custom_days_entry.grid(row=2, column=2, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Custom nights").grid(row=1, column=3, sticky="w", padx=10)
        self.custom_nights_entry = ctk.CTkEntry(frame)
        self.custom_nights_entry.grid(row=2, column=3, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Return date flexibility").grid(row=3, column=0, sticky="w", padx=10)
        self.return_flex_menu = ctk.CTkOptionMenu(frame, values=list(RETURN_FLEX_OPTIONS.keys()))
        self.return_flex_menu.set("±1 day")
        self.return_flex_menu.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

        self.auto_calc_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Auto-calculate DOWN dates", variable=self.auto_calc_var).grid(
            row=4, column=1, sticky="w", padx=10, pady=(0, 8)
        )

        ctk.CTkLabel(frame, text="Return calculation rule").grid(row=3, column=2, sticky="w", padx=10)
        self.return_rule_menu = ctk.CTkOptionMenu(frame, values=RETURN_CALC_RULES)
        self.return_rule_menu.grid(row=4, column=2, columnspan=2, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Manual DOWN date from (if manual mode)").grid(row=5, column=0, sticky="w", padx=10)
        self.manual_down_from_entry = ctk.CTkEntry(frame, placeholder_text="2026-08-14")
        self.manual_down_from_entry.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Manual DOWN date to (if manual mode)").grid(row=5, column=1, sticky="w", padx=10)
        self.manual_down_to_entry = ctk.CTkEntry(frame, placeholder_text="2026-08-19")
        self.manual_down_to_entry.grid(row=6, column=1, sticky="ew", padx=10, pady=(0, 8))

        self.cost_estimate_label = ctk.CTkLabel(frame, text="", justify="left", anchor="w")
        self.cost_estimate_label.grid(row=7, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 10))

    def _on_duration_mode_change(self, _value):
        pass

    def _on_preset_change(self, value):
        for label, days, nights in DURATION_PRESETS:
            if label == value and days is not None:
                self.custom_days_entry.delete(0, "end")
                self.custom_days_entry.insert(0, str(days))
                self.custom_nights_entry.delete(0, "end")
                self.custom_nights_entry.insert(0, str(nights))

    # ------------------------------------------------------------- filters
    def _build_filters_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=5, column=0, sticky="ew", padx=10, pady=10)
        for i in range(4):
            frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(frame, text="FILTERS", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5)
        )

        ctk.CTkLabel(frame, text="Max stops").grid(row=1, column=0, sticky="w", padx=10)
        self.max_stops_menu = ctk.CTkOptionMenu(frame, values=list(MAX_STOPS_OPTIONS.keys()))
        self.max_stops_menu.set("Max 1 stop")
        self.max_stops_menu.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Max layover").grid(row=1, column=1, sticky="w", padx=10)
        self.max_layover_menu = ctk.CTkOptionMenu(frame, values=list(MAX_LAYOVER_OPTIONS.keys()))
        self.max_layover_menu.set("6 hours")
        self.max_layover_menu.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Min layover").grid(row=1, column=2, sticky="w", padx=10)
        self.min_layover_menu = ctk.CTkOptionMenu(frame, values=list(MIN_LAYOVER_OPTIONS.keys()))
        self.min_layover_menu.set("1 hour 15 minutes")
        self.min_layover_menu.grid(row=2, column=2, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Baggage required").grid(row=1, column=3, sticky="w", padx=10)
        self.baggage_menu = ctk.CTkOptionMenu(frame, values=BAGGAGE_OPTIONS)
        self.baggage_menu.set("Checked baggage required")
        self.baggage_menu.grid(row=2, column=3, sticky="ew", padx=10, pady=(0, 8))

        self.avoid_airport_change_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Avoid airport change during layover", variable=self.avoid_airport_change_var).grid(
            row=3, column=0, sticky="w", padx=10, pady=(0, 8)
        )
        self.avoid_midnight_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Avoid arrival after midnight", variable=self.avoid_midnight_var).grid(
            row=3, column=1, sticky="w", padx=10, pady=(0, 8)
        )
        self.avoid_overnight_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text="Avoid overnight layover", variable=self.avoid_overnight_var).grid(
            row=3, column=2, sticky="w", padx=10, pady=(0, 8)
        )
        self.same_day_arrival_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text="Prefer same-day arrival", variable=self.same_day_arrival_var).grid(
            row=3, column=3, sticky="w", padx=10, pady=(0, 8)
        )
        self.same_airline_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text="Same airline both ways preferred", variable=self.same_airline_var).grid(
            row=4, column=0, sticky="w", padx=10, pady=(0, 8)
        )

        ctk.CTkLabel(frame, text="Preferred airlines (comma separated)").grid(row=5, column=0, sticky="w", padx=10)
        self.preferred_airlines_entry = ctk.CTkEntry(frame)
        self.preferred_airlines_entry.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Blocked airlines (comma separated)").grid(row=5, column=2, sticky="w", padx=10)
        self.blocked_airlines_entry = ctk.CTkEntry(frame)
        self.blocked_airlines_entry.grid(row=6, column=2, columnspan=2, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Maximum fare per person (blank = no limit)").grid(row=7, column=0, sticky="w", padx=10)
        self.max_fare_entry = ctk.CTkEntry(frame)
        self.max_fare_entry.grid(row=8, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Sort preference").grid(row=7, column=1, sticky="w", padx=10)
        self.sort_menu = ctk.CTkOptionMenu(frame, values=SORT_PREFERENCES)
        self.sort_menu.set("Best value")
        self.sort_menu.grid(row=8, column=1, sticky="ew", padx=10, pady=(0, 8))

    # --------------------------------------------------------- commercials
    def _build_commercials_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=6, column=0, sticky="ew", padx=10, pady=10)
        for i in range(4):
            frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(frame, text="COMMERCIALS", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5)
        )

        ctk.CTkLabel(frame, text="Markup type").grid(row=1, column=0, sticky="w", padx=10)
        self.markup_type_menu = ctk.CTkOptionMenu(frame, values=MARKUP_TYPES)
        self.markup_type_menu.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Markup value").grid(row=1, column=1, sticky="w", padx=10)
        self.markup_value_entry = ctk.CTkEntry(frame)
        self.markup_value_entry.insert(0, "0")
        self.markup_value_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Round final price").grid(row=1, column=2, sticky="w", padx=10)
        self.rounding_menu = ctk.CTkOptionMenu(frame, values=list(ROUNDING_OPTIONS.keys()))
        self.rounding_menu.grid(row=2, column=2, sticky="ew", padx=10, pady=(0, 8))

        self.show_api_fare_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Show API fare in staff view", variable=self.show_api_fare_var).grid(
            row=3, column=0, sticky="w", padx=10, pady=(0, 8)
        )

    # ---------------------------------------------------------------- core
    def build_request(self):
        try:
            adults = int(self.adults_entry.get() or 0)
            children = int(self.children_entry.get() or 0)
            infants = int(self.infants_entry.get() or 0)
        except ValueError:
            raise ValueError("Adults, children, and infants must be whole numbers.")
        if adults < 1:
            raise ValueError("At least 1 adult is required.")

        passengers = PassengerInfo(adults=adults, children=children, infants=infants)

        up_route = self.up_section.to_route_query("UP / Onward flight")
        down_route = self.down_section.to_route_query("DOWN / Return flight")

        mode_label = self.duration_mode_menu.get()
        mode = {
            "Fixed package duration": "fixed",
            "Custom date gap": "custom_gap",
            "Manual return date range": "manual",
        }[mode_label]

        try:
            days = int(self.custom_days_entry.get())
            nights = int(self.custom_nights_entry.get())
        except ValueError:
            raise ValueError("Package duration days/nights must be numbers.")

        manual_down_start = manual_down_end = None
        if mode == "manual":
            manual_down_start = _parse_date(self.manual_down_from_entry.get(), "Manual DOWN date from")
            manual_down_end = _parse_date(self.manual_down_to_entry.get(), "Manual DOWN date to")

        duration = PackageDuration(
            mode=mode,
            label=self.duration_preset_menu.get(),
            days=days,
            nights=nights,
            return_flex_days=RETURN_FLEX_OPTIONS[self.return_flex_menu.get()],
            auto_calculate_down_dates=self.auto_calc_var.get(),
            return_calc_rule=self.return_rule_menu.get(),
            manual_down_start=manual_down_start,
            manual_down_end=manual_down_end,
        )

        max_layover_label = self.max_layover_menu.get()
        max_layover = MAX_LAYOVER_OPTIONS.get(max_layover_label) or 360

        max_fare_text = self.max_fare_entry.get().strip()
        max_fare = float(max_fare_text) if max_fare_text else None

        preferred_airlines = [a.strip() for a in self.preferred_airlines_entry.get().split(",") if a.strip()]
        blocked_airlines = [a.strip() for a in self.blocked_airlines_entry.get().split(",") if a.strip()]

        filters = SearchFilters(
            max_stops=MAX_STOPS_OPTIONS[self.max_stops_menu.get()],
            max_layover_minutes=max_layover,
            min_layover_minutes=MIN_LAYOVER_OPTIONS[self.min_layover_menu.get()],
            avoid_airport_change=self.avoid_airport_change_var.get(),
            avoid_arrival_after_midnight=self.avoid_midnight_var.get(),
            avoid_overnight_layover=self.avoid_overnight_var.get(),
            prefer_same_day_arrival=self.same_day_arrival_var.get(),
            baggage_required=self.baggage_menu.get(),
            preferred_airlines=preferred_airlines,
            blocked_airlines=blocked_airlines,
            same_airline_both_ways_preferred=self.same_airline_var.get(),
            max_fare_per_person=max_fare,
            sort_preference=self.sort_menu.get(),
        )

        rounding = ROUNDING_OPTIONS.get(self.rounding_menu.get())
        markup_value_text = self.markup_value_entry.get().strip() or "0"
        try:
            markup_value = float(markup_value_text)
        except ValueError:
            raise ValueError("Markup value must be a number.")

        customer_name = self.customer_entry.get().strip() or "Customer"
        package_name = self.package_entry.get().strip() or "Tour Package"

        return FlightSearchRequest(
            customer_name=customer_name,
            package_name=package_name,
            passengers=passengers,
            travel_class=self.travel_class_menu.get(),
            currency=self.currency_menu.get(),
            up_route=up_route,
            down_route=down_route,
            duration=duration,
            filters=filters,
            markup_type=self.markup_type_menu.get(),
            markup_value=markup_value,
            rounding=rounding,
        )

    def _handle_search(self):
        try:
            request = self.build_request()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        try:
            pairs = generate_date_pairs(
                up_start_date=request.up_route.date_from,
                up_end_date=request.up_route.date_to,
                duration_days=request.duration.days,
                duration_nights=request.duration.nights,
                return_flex_days=request.duration.return_flex_days,
                manual_down_start=request.duration.manual_down_start,
                manual_down_end=request.duration.manual_down_end,
                mode=request.duration.mode,
            )
        except ValueError as exc:
            messagebox.showerror("Invalid date range", str(exc))
            return

        cost = estimate_search_cost(pairs)
        self.cost_estimate_label.configure(
            text=(
                f"UP dates: {cost['up_dates']}  |  DOWN dates: {cost['down_dates']}  |  "
                f"Valid date pairs: {cost['date_pairs']}  |  "
                f"Estimated API calls: {cost['estimated_api_calls']}\n"
                f"More date flexibility increases API usage."
            )
        )

        if cost["date_pairs"] == 0:
            messagebox.showerror(
                "No valid date pairs",
                "No valid UP/DOWN date pairs were generated. Check your date ranges, "
                "package duration, and that DOWN dates fall after UP dates.",
            )
            return

        if cost["estimated_api_calls"] > API_CALL_WARNING_THRESHOLD:
            proceed = messagebox.askyesno(
                "Confirm search",
                f"This search is estimated to use {cost['estimated_api_calls']} API calls "
                f"across {cost['date_pairs']} date pairs. More date flexibility increases "
                f"API usage. Continue?",
            )
            if not proceed:
                return

        self.on_search(request)
