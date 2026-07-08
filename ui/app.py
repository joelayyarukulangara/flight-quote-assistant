"""Main application window: wires together the four tabs."""
import json
from datetime import datetime, date
from tkinter import messagebox

import customtkinter as ctk

import database
from config import APP_NAME
from models import (
    PassengerInfo, RouteQuery, PackageDuration, SearchFilters, FlightSearchRequest,
    FlightOption, Layover, PackageFlightCombination, QuoteResult,
)
from services.search_service import run_search, SearchError
from services.export_service import build_whatsapp_text, export_pdf, export_excel, ExportError
from services.ai_summary_service import generate_customer_quote_summary, build_rule_based_summary
from ui.search_form import SearchForm
from ui.results_view import ResultsView
from ui.settings_view import SettingsView

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def _flight_from_dict(d):
    layovers = [Layover(**l) for l in d.get("layovers", [])]
    return FlightOption(
        provider=d["provider"], airline=d["airline"], airline_code=d["airline_code"],
        flight_number=d["flight_number"], origin=d["origin"], destination=d["destination"],
        departure_datetime=datetime.fromisoformat(d["departure_datetime"]),
        arrival_datetime=datetime.fromisoformat(d["arrival_datetime"]),
        duration_minutes=d["duration_minutes"], stops=d["stops"], layovers=layovers,
        layover_minutes_total=d["layover_minutes_total"],
        airport_change_required=d["airport_change_required"], baggage_info=d["baggage_info"],
        refund_info=d["refund_info"], fare=d["fare"], currency=d["currency"],
        booking_source=d.get("booking_source", ""), warnings=d.get("warnings", []),
    )


def _combo_from_dict(d):
    return PackageFlightCombination(
        up_flight=_flight_from_dict(d["up_flight"]),
        down_flight=_flight_from_dict(d["down_flight"]),
        package_days=d["package_days"], package_nights=d["package_nights"],
        total_base_fare_per_person=d["total_base_fare_per_person"],
        markup_amount=d["markup_amount"], final_quote_per_person=d["final_quote_per_person"],
        total_group_fare=d["total_group_fare"], score=d["score"], category=d["category"],
        warnings=d.get("warnings", []),
        price_checked_at=datetime.fromisoformat(d["price_checked_at"]) if d.get("price_checked_at") else None,
        source=d.get("source", "Mock"),
    )


def _request_from_dict(d):
    up = d["up_route"]
    down = d["down_route"]
    duration = d["duration"]
    return FlightSearchRequest(
        customer_name=d["customer_name"], package_name=d["package_name"],
        passengers=PassengerInfo(**d["passengers"]), travel_class=d["travel_class"],
        currency=d["currency"],
        up_route=RouteQuery(
            origin=up["origin"], destination=up["destination"],
            date_from=date.fromisoformat(up["date_from"]), date_to=date.fromisoformat(up["date_to"]),
            preferred_departure_time=up["preferred_departure_time"],
            preferred_arrival_time=up["preferred_arrival_time"],
            allow_nearby_origin=up["allow_nearby_origin"], allow_nearby_destination=up["allow_nearby_destination"],
        ),
        down_route=RouteQuery(
            origin=down["origin"], destination=down["destination"],
            date_from=date.fromisoformat(down["date_from"]), date_to=date.fromisoformat(down["date_to"]),
            preferred_departure_time=down["preferred_departure_time"],
            preferred_arrival_time=down["preferred_arrival_time"],
            allow_nearby_origin=down["allow_nearby_origin"], allow_nearby_destination=down["allow_nearby_destination"],
        ),
        duration=PackageDuration(
            mode=duration["mode"], label=duration["label"], days=duration["days"], nights=duration["nights"],
            min_nights=duration.get("min_nights"), max_nights=duration.get("max_nights"),
            return_flex_days=duration["return_flex_days"],
            auto_calculate_down_dates=duration["auto_calculate_down_dates"],
            return_calc_rule=duration["return_calc_rule"],
            manual_down_start=date.fromisoformat(duration["manual_down_start"]) if duration.get("manual_down_start") else None,
            manual_down_end=date.fromisoformat(duration["manual_down_end"]) if duration.get("manual_down_end") else None,
        ),
        filters=SearchFilters(**d["filters"]),
        markup_type=d["markup_type"], markup_value=d["markup_value"], rounding=d.get("rounding"),
    )


class SavedQuotesView(ctk.CTkFrame):
    def __init__(self, parent, on_open_result):
        super().__init__(parent)
        self.on_open_result = on_open_result
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.search_entry = ctk.CTkEntry(toolbar, placeholder_text="Search by customer or package name")
        self.search_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)
        ctk.CTkButton(toolbar, text="Search", command=self.refresh).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Refresh List", command=self.refresh).pack(side="left", padx=5)

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.refresh()

    def refresh(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        rows = database.list_saved_quotes(self.search_entry.get().strip())
        if not rows:
            ctk.CTkLabel(self.list_frame, text="No saved quotes yet.").grid(row=0, column=0, sticky="w", padx=10, pady=10)
            return

        for i, row in enumerate(rows):
            card = ctk.CTkFrame(self.list_frame, corner_radius=8, border_width=1)
            card.grid(row=i, column=0, sticky="ew", padx=5, pady=5)
            card.grid_columnconfigure(0, weight=1)

            info = (
                f"{row['customer_name']} — {row['package_name']}\n"
                f"Created: {row['created_at'][:16]}   Last refreshed: {row['last_refreshed_at'][:16]}"
            )
            ctk.CTkLabel(card, text=info, justify="left", anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=8)

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.grid(row=0, column=1, sticky="e", padx=10)
            ctk.CTkButton(btns, text="View", width=70, command=lambda r=row: self._view(r)).pack(side="left", padx=3)
            ctk.CTkButton(btns, text="Refresh Price", width=100, command=lambda r=row: self._refresh_price(r)).pack(side="left", padx=3)
            ctk.CTkButton(btns, text="Delete", width=70, fg_color="#a83232", hover_color="#7a2424",
                          command=lambda r=row: self._delete(r)).pack(side="left", padx=3)

    def _load_quote_result(self, row):
        request = _request_from_dict(json.loads(row["request_json"]))
        combos = [_combo_from_dict(c) for c in json.loads(row["result_json"])]
        from config import FARE_WARNING_TEXT
        from utils.date_utils import now_str
        return QuoteResult(request=request, combinations=combos, generated_at=datetime.now(),
                            fare_warning=FARE_WARNING_TEXT.format(timestamp=now_str()))

    def _view(self, row):
        try:
            quote_result = self._load_quote_result(row)
        except Exception as exc:
            messagebox.showerror("Could not open quote", f"This saved quote could not be loaded: {exc}")
            return
        self.on_open_result(quote_result)

    def _refresh_price(self, row):
        try:
            quote_result = self._load_quote_result(row)
            new_result = run_search(quote_result.request, force_refresh=True)
        except (SearchError, Exception) as exc:
            messagebox.showerror("Refresh failed", str(exc))
            return
        result_json = json.dumps([c.to_dict() for c in new_result.combinations])
        database.update_saved_quote(row["id"], result_json=result_json)
        messagebox.showinfo("Refreshed", "Saved quote price refreshed.")
        self.refresh()
        self.on_open_result(new_result)

    def _delete(self, row):
        if messagebox.askyesno("Delete quote", f"Delete saved quote for {row['customer_name']}?"):
            database.delete_saved_quote(row["id"])
            self.refresh()


class FlightQuoteApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1100x800")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_new_quote = self.tabview.add("New Quote")
        self.tab_results = self.tabview.add("Results")
        self.tab_saved = self.tabview.add("Saved Quotes")
        self.tab_settings = self.tabview.add("Settings")

        for tab in (self.tab_new_quote, self.tab_results, self.tab_saved, self.tab_settings):
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self.results_view = ResultsView(self.tab_results, self._get_settings)
        self.results_view.grid(row=0, column=0, sticky="nsew")

        self.search_form = SearchForm(self.tab_new_quote, self._handle_search)
        self.search_form.grid(row=0, column=0, sticky="nsew")

        self.saved_quotes_view = SavedQuotesView(self.tab_saved, self._open_result_in_results_tab)
        self.saved_quotes_view.grid(row=0, column=0, sticky="nsew")

        self.settings_view = SettingsView(self.tab_settings)
        self.settings_view.grid(row=0, column=0, sticky="nsew")

    def _get_settings(self):
        return database.get_all_settings()

    def _handle_search(self, request):
        try:
            result = run_search(request)
        except SearchError as exc:
            self.results_view.show_error(str(exc))
            self.tabview.set("Results")
            return
        except Exception as exc:  # never crash on unexpected provider/data errors
            self.results_view.show_error(f"Search failed unexpectedly: {exc}")
            self.tabview.set("Results")
            return
        self.results_view.show_result(result)
        self.tabview.set("Results")

    def _open_result_in_results_tab(self, quote_result):
        self.results_view.show_result(quote_result)
        self.tabview.set("Results")


def launch_app():
    app = FlightQuoteApp()
    app.mainloop()
