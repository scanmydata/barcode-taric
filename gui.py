#!/usr/bin/env python3
"""Tkinter GUI for the Barcode → TARIC lookup tool."""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Any
import urllib.error

from taric_lookup import load_inputs, resolve_item

_MAX_PRODUCT_LABEL_LEN = 60


class BarcodeApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Barcode → TARIC Lookup")
        self.minsize(860, 620)
        self.resizable(True, True)
        self._results: list[dict[str, Any]] = []
        self._queue: queue.Queue[list[dict[str, Any]] | Exception] = queue.Queue()
        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_input_frame()
        self._build_results_frame()
        self._build_status_bar()

    def _build_input_frame(self) -> None:
        frame = ttk.LabelFrame(self, text="Input", padding=8)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        frame.columnconfigure(1, weight=1)

        # Single entry row
        ttk.Label(frame, text="Barcode / Description:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self._entry_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self._entry_var, width=40)
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<Return>", lambda _: self._on_add())
        ttk.Button(frame, text="Add", command=self._on_add).grid(row=0, column=2, padx=(6, 0))

        # Listbox with items
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        list_frame.columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(list_frame, height=5, selectmode=tk.EXTENDED, activestyle="none")
        self._listbox.grid(row=0, column=0, sticky="ew")
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._listbox.configure(yscrollcommand=sb.set)

        # Buttons row
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Button(btn_frame, text="Load File…", command=self._on_load_file).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Remove Selected", command=self._on_remove).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Clear All", command=self._on_clear).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Label(btn_frame, text="AI Provider:").pack(side=tk.LEFT, padx=(0, 4))
        self._ai_provider = tk.StringVar(value="pollinations")
        provider_cb = ttk.Combobox(
            btn_frame,
            textvariable=self._ai_provider,
            values=["pollinations", "openrouter", "none"],
            state="readonly",
            width=14,
        )
        provider_cb.pack(side=tk.LEFT, padx=(0, 12))

        self._search_btn = ttk.Button(btn_frame, text="🔍  Search TARIC Codes", command=self._on_search)
        self._search_btn.pack(side=tk.LEFT)

        self._progress = ttk.Progressbar(btn_frame, mode="indeterminate", length=120)
        self._progress.pack(side=tk.LEFT, padx=(8, 0))

    def _build_results_frame(self) -> None:
        frame = ttk.LabelFrame(self, text="Results", padding=8)
        frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 4))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("input", "product", "taric_code", "description")
        self._tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("input", text="Input")
        self._tree.heading("product", text="Product Found")
        self._tree.heading("taric_code", text="TARIC Code")
        self._tree.heading("description", text="Customs Description")

        self._tree.column("input", width=160, minwidth=100)
        self._tree.column("product", width=230, minwidth=130)
        self._tree.column("taric_code", width=120, minwidth=90, anchor="center")
        self._tree.column("description", width=320, minwidth=160)

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._tree.yview)
        hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        export_frame = ttk.Frame(frame)
        export_frame.grid(row=2, column=0, columnspan=2, sticky="e", pady=(6, 0))
        ttk.Button(export_frame, text="Copy Row", command=self._on_copy_row).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(export_frame, text="Export JSON…", command=self._on_export).pack(side=tk.LEFT)

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Ready")
        bar = ttk.Label(self, textvariable=self._status_var, relief=tk.SUNKEN, anchor=tk.W)
        bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)

    # ------------------------------------------------------------------
    # Input management
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        value = self._entry_var.get().strip()
        if not value:
            return
        for existing in self._listbox.get(0, tk.END):
            if existing == value:
                self._status_var.set(f"Already in list: {value}")
                return
        self._listbox.insert(tk.END, value)
        self._entry_var.set("")
        self._status_var.set(f"Added: {value}")

    def _on_remove(self) -> None:
        selected = list(self._listbox.curselection())
        for index in reversed(selected):
            self._listbox.delete(index)

    def _on_clear(self) -> None:
        self._listbox.delete(0, tk.END)
        self._status_var.set("List cleared")

    def _on_load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select input file",
            filetypes=[
                ("Text / CSV / Excel", "*.txt *.csv *.tsv *.xlsx *.xlsm"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            items = load_inputs(Path(path))
        except (ValueError, OSError) as exc:
            messagebox.showerror("Load error", str(exc))
            return
        added = 0
        existing = set(self._listbox.get(0, tk.END))
        for item in items:
            if item not in existing:
                self._listbox.insert(tk.END, item)
                existing.add(item)
                added += 1
        self._status_var.set(f"Loaded {added} item(s) from {Path(path).name}")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self) -> None:
        items = list(self._listbox.get(0, tk.END))
        if not items:
            messagebox.showwarning("No input", "Add at least one barcode or product description.")
            return

        self._search_btn.config(state=tk.DISABLED)
        self._progress.start(12)
        self._status_var.set(f"Looking up {len(items)} item(s)…")
        provider = self._ai_provider.get()

        def worker() -> None:
            try:
                results = [resolve_item(item, ai_provider=provider) for item in items]
                self._queue.put(results)
        except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:  # noqa: BLE001
                self._queue.put(exc)

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self) -> None:
        try:
            result = self._queue.get_nowait()
            self._progress.stop()
            self._search_btn.config(state=tk.NORMAL)
            if isinstance(result, Exception):
                self._status_var.set(f"Error: {result}")
                messagebox.showerror("Lookup error", str(result))
            else:
                self._display_results(result)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _display_results(self, results: list[dict[str, Any]]) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)

        for r in results:
            match = r.get("match", {})
            src = r.get("source", {})
            product_label = src.get("product_name") or r.get("commercial_text", "")
            if product_label:
                product_label = str(product_label)[:_MAX_PRODUCT_LABEL_LEN]

            taric_raw = match.get("taric_code") or ""
            taric_display = _format_taric(taric_raw) if taric_raw else "—"

            self._tree.insert(
                "",
                tk.END,
                values=(
                    r.get("input", ""),
                    product_label or "—",
                    taric_display,
                    match.get("description") or "—",
                ),
            )

        self._results = results
        self._status_var.set(f"Done — {len(results)} result(s)")

    def _on_copy_row(self) -> None:
        selected = self._tree.selection()
        if not selected:
            self._status_var.set("Select a row first")
            return
        values = self._tree.item(selected[0], "values")
        text = "\t".join(str(v) for v in values)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status_var.set("Row copied to clipboard")

    def _on_export(self) -> None:
        if not self._results:
            messagebox.showwarning("No results", "Run a search first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export results",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(
            json.dumps(self._results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._status_var.set(f"Exported to {path}")
        messagebox.showinfo("Exported", f"Saved {len(self._results)} result(s) to:\n{path}")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _format_taric(code: str) -> str:
    """Format a 10-digit TARIC code as XXXX XX XX XX."""
    digits = "".join(c for c in code if c.isdigit())
    if len(digits) == 10:
        return f"{digits[:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}"
    return code


def main() -> None:
    app = BarcodeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
