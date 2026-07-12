"""Results tab: shows the best 4 quote-ready package combinations."""
import json
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

import database
from services.export_service import build_whatsapp_text, export_pdf, export_excel, ExportError
from services.search_service import run_search, SearchError
from services.ai_summary_service import generate_customer_quote_summary
from utils.date_utils import format_datetime, now_str


class ResultCard(ctk.CTkFrame):
    def __init__(self, parent, combo, currency, index, staff_view=True):
        super().__init__(parent, corner_radius=10, border_width=1)
        self.combo = combo
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            self, text=f"Option {index}: {combo.category}",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        header.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

        duration_label = ctk.CTkLabel(self, text=f"Package: {combo.package_days} Days / {combo.package_nights} Nights")
        duration_label.grid(row=1, column=0, sticky="w", padx=12)

        self._add_leg(row=2, label="UP", flight=combo.up_flight, staff_view=staff_view)
        self._add_leg(row=3, label="DOWN", flight=combo.down_flight, staff_view=staff_view)

        fare_frame = ctk.CTkFrame(self, fg_color="transparent")
        fare_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(6, 4))

        if staff_view:
            ctk.CTkLabel(
                fare_frame,
                text=f"Base fare: {currency} {combo.total_base_fare_per_person:,.0f}  |  "
                     f"Markup: {currency} {combo.markup_amount:,.0f}",
            ).pack(anchor="w")

        ctk.CTkLabel(
            fare_frame,
            text=f"Final quote: {currency} {combo.final_quote_per_person:,.0f} per person   "
                 f"(Total group: {currency} {combo.total_group_fare:,.0f})",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")

        if combo.warnings:
            warn_text = "; ".join(combo.warnings)
            ctk.CTkLabel(self, text=f"⚠ {warn_text}", text_color="#d98c00", wraplength=520, justify="left").grid(
                row=5, column=0, sticky="w", padx=12, pady=(0, 4)
            )

        meta = f"Price checked: {combo.price_checked_at.strftime('%d %b %Y, %I:%M %p') if combo.price_checked_at else now_str()}   |   Source: {combo.source}"
        ctk.CTkLabel(self, text=meta, text_color="gray", font=ctk.CTkFont(size=11)).grid(
            row=6, column=0, sticky="w", padx=12, pady=(0, 10)
        )

    def _add_leg(self, row, label, flight, staff_view):
        text_lines = [
            f"{label}: {flight.origin} → {flight.destination}   {flight.airline}"
            + (f" ({flight.flight_number})" if staff_view and flight.flight_number else ""),
            f"   Depart: {format_datetime(flight.departure_datetime)}   Arrive: {format_datetime(flight.arrival_datetime)}",
            f"   Duration: {flight.duration_minutes // 60}h {flight.duration_minutes % 60}m   "
            f"Stops: {flight.stops}"
            + (f"   Layover: {flight.layover_minutes_total} min" if flight.stops else ""),
            f"   Fare: {flight.currency} {flight.fare:,.0f}   Baggage: {flight.baggage_info}",
        ]
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=2)
        for line in text_lines:
            ctk.CTkLabel(frame, text=line, justify="left", anchor="w").pack(anchor="w")


class ResultsView(ctk.CTkScrollableFrame):
    def __init__(self, parent, get_settings):
        super().__init__(parent, label_text="Results")
        self.get_settings = get_settings
        self.quote_result = None
        self.staff_view_var = ctk.BooleanVar(value=True)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()
        self.status_label = ctk.CTkLabel(self, text="Run a search from the New Quote tab to see results here.")
        self.status_label.grid(row=1, column=0, sticky="w", padx=10, pady=10)

        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.grid(row=2, column=0, sticky="nsew", padx=10)
        self.grid_columnconfigure(0, weight=1)

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkSwitch(toolbar, text="Staff view (show internal fare detail)", variable=self.staff_view_var,
                      command=self._rerender).pack(side="left", padx=(0, 15))
        ctk.CTkButton(toolbar, text="Copy WhatsApp Quote", command=self._copy_whatsapp).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Export PDF", command=self._export_pdf).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Export Excel", command=self._export_excel).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save Quote", command=self._save_quote).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Refresh Price", command=self._refresh_price).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Generate AI Quote", command=self._generate_ai_quote).pack(side="left", padx=5)

    def show_result(self, quote_result):
        self.quote_result = quote_result
        self._rerender()

    def show_error(self, message):
        self.quote_result = None
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        self.status_label.configure(text=message, text_color="#d98c00")

    def _rerender(self):
        for widget in self.cards_frame.winfo_children():
            widget.destroy()

        if not self.quote_result:
            self.status_label.configure(text="Run a search from the New Quote tab to see results here.", text_color=("black", "white"))
            return

        request = self.quote_result.request
        self.status_label.configure(
            text=f"Best {len(self.quote_result.combinations)} package options for "
                 f"{request.customer_name} — {request.package_name}",
            text_color=("black", "white"),
        )

        for i, combo in enumerate(self.quote_result.combinations, start=1):
            card = ResultCard(self.cards_frame, combo, request.currency, i, staff_view=self.staff_view_var.get())
            card.grid(row=i - 1, column=0, sticky="ew", pady=6)
        self.cards_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkLabel(
            self.cards_frame, text=self.quote_result.fare_warning, text_color="gray",
            wraplength=700, justify="left",
        )
        footer.grid(row=len(self.quote_result.combinations), column=0, sticky="w", pady=10)

    def _require_result(self):
        if not self.quote_result:
            messagebox.showinfo("No results", "Run a search first.")
            return False
        return True

    def _copy_whatsapp(self):
        if not self._require_result():
            return
        company = database.get_setting("company_name", "Your Travel Company")
        text = build_whatsapp_text(self.quote_result, company)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "WhatsApp-ready quote copied to clipboard.")

    def _export_pdf(self):
        if not self._require_result():
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            company = database.get_setting("company_name", "Your Travel Company")
            export_pdf(self.quote_result, path, company)
            messagebox.showinfo("Exported", f"PDF quote saved to {path}")
        except ExportError as exc:
            messagebox.showerror("Export failed", str(exc))

    def _export_excel(self):
        if not self._require_result():
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            export_excel(self.quote_result, path)
            messagebox.showinfo("Exported", f"Excel comparison sheet saved to {path}")
        except ExportError as exc:
            messagebox.showerror("Export failed", str(exc))

    def _save_quote(self):
        if not self._require_result():
            return
        request = self.quote_result.request
        request_json = json.dumps(_serialize_request(request))
        result_json = json.dumps([c.to_dict() for c in self.quote_result.combinations])
        quote_id = database.save_quote(request.customer_name, request.package_name, request_json, result_json)
        messagebox.showinfo("Saved", f"Quote saved (ID {quote_id}). See Saved Quotes tab.")

    def _refresh_price(self):
        if not self._require_result():
            return
        try:
            new_result = run_search(self.quote_result.request, force_refresh=True)
            self.show_result(new_result)
            messagebox.showinfo("Refreshed", "Prices refreshed from live source (or mock data).")
        except SearchError as exc:
            messagebox.showerror("Search failed", str(exc))

    def _generate_ai_quote(self):
        if not self._require_result():
            return
        settings = database.get_all_settings()
        if settings.get("enable_ai_summary", "false") != "true" or not settings.get("openai_api_key"):
            messagebox.showinfo(
                "AI summary disabled",
                "AI summary is disabled or no OpenAI API key is set (see Settings tab). "
                "A standard rule-based quote will be used instead.",
            )
        request = self.quote_result.request
        customer_info = {"name": request.customer_name}
        package_info = {"name": request.package_name}
        text, warning = generate_customer_quote_summary(
            self.quote_result, customer_info, package_info,
            api_key=settings.get("openai_api_key", ""),
            model=settings.get("ai_model_name", "gpt-4o-mini"),
            language=settings.get("ai_language", "English"),
            base_url=settings.get("ai_base_url", "https://api.openai.com/v1"),
        )
        self.clipboard_clear()
        self.clipboard_append(text)
        if warning:
            messagebox.showwarning("AI Quote", f"{warning}\n\nQuote text copied to clipboard.")
        else:
            messagebox.showinfo("AI Quote", "AI-generated customer quote copied to clipboard.")


def _serialize_request(request):
    from dataclasses import asdict
    d = asdict(request)
    for route_key in ("up_route", "down_route"):
        d[route_key]["date_from"] = request.__getattribute__(route_key).date_from.isoformat()
        d[route_key]["date_to"] = request.__getattribute__(route_key).date_to.isoformat()
    if request.duration.manual_down_start:
        d["duration"]["manual_down_start"] = request.duration.manual_down_start.isoformat()
    if request.duration.manual_down_end:
        d["duration"]["manual_down_end"] = request.duration.manual_down_end.isoformat()
    return d
