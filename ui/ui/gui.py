from __future__ import annotations

import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class LibraryGUI:
    """Desktop GUI for the existing xToys Library Manager application layer."""

    def __init__(self, application):
        self.application = application
        self.root = tk.Tk()
        self.root.title("xToys Library Manager")
        self.root.geometry("560x420")
        self.root.minsize(500, 360)

        self.status_var = tk.StringVar(value="Ready")
        self.count_var = tk.StringVar(value="")
        self._build_main_window()
        self.refresh_count()

    def _build_main_window(self):
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="xToys Library Manager",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(pady=(8, 6))

        ttk.Label(
            outer,
            textvariable=self.count_var,
            font=("TkDefaultFont", 11),
        ).pack(pady=(0, 24))

        actions = ttk.Frame(outer)
        actions.pack(fill="x")

        self._button(actions, "Add Funscript", self.add_funscript, 0, 0)
        self._button(actions, "View Funscripts", self.view_funscripts, 0, 1)
        self._button(actions, "Rebuild Library", self.rebuild_library, 1, 0)
        self._button(actions, "Build index.json", self.build_index, 1, 1)
        self._button(actions, "Validate Library", self.validate_library, 2, 0)
        self._button(actions, "Settings", self.show_settings, 2, 1)

        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)

        status = ttk.LabelFrame(outer, text="Status", padding=10)
        status.pack(fill="x", side="bottom", pady=(24, 0))
        ttk.Label(status, textvariable=self.status_var).pack(anchor="w")

    @staticmethod
    def _button(parent, text, command, row, column):
        button = ttk.Button(parent, text=text, command=command)
        button.grid(row=row, column=column, sticky="ew", padx=6, pady=6, ipady=8)
        return button

    def run(self):
        self.root.mainloop()

    def refresh_count(self):
        try:
            count = len(self.application.database.all_scripts())
            self.count_var.set(f"Library: {count} funscripts")
        except Exception:
            self.count_var.set("Library: unavailable")

    def set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    def add_funscript(self):
        """Open the Add Funscript dialog.

        Users can either import an EroScripts page by URL or select
        existing .funscript files from the local computer.
        """
        window = tk.Toplevel(self.root)
        window.title("Add Funscript")
        window.geometry("620x330")
        window.minsize(560, 300)
        window.transient(self.root)
        window.grab_set()

        outer = ttk.Frame(window, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Add Funscript",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(
            outer,
            text="Import a funscript from an EroScripts page or from your computer.",
        ).pack(anchor="w", pady=(0, 18))

        url_frame = ttk.LabelFrame(outer, text="Import from EroScripts URL", padding=12)
        url_frame.pack(fill="x", pady=(0, 14))

        url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=url_var)
        url_entry.pack(fill="x", pady=(0, 10))
        url_entry.focus_set()

        url_status = tk.StringVar(value="")
        ttk.Label(url_frame, textvariable=url_status).pack(anchor="w", pady=(0, 8))

        button_row = ttk.Frame(url_frame)
        button_row.pack(fill="x")

        import_button = ttk.Button(button_row, text="Import from URL")
        import_button.pack(side="left")

        ttk.Label(
            outer,
            text="Or import .funscript files already on this computer:",
        ).pack(anchor="w", pady=(4, 8))

        ttk.Button(
            outer,
            text="Choose Local Funscript Files",
            command=lambda: (window.destroy(), self.add_local_funscripts()),
        ).pack(anchor="w")

        ttk.Button(
            outer,
            text="Cancel",
            command=window.destroy,
        ).pack(anchor="e", pady=(20, 0))

        def start_import():
            url = url_var.get().strip()
            if not url:
                messagebox.showwarning(
                    "URL Required",
                    "Paste an EroScripts page URL first.",
                    parent=window,
                )
                return

            import_button.config(state="disabled")
            url_entry.config(state="disabled")
            url_status.set("Importing... A browser window may open for EroScripts login.")
            self.set_status("Importing funscript(s) from EroScripts...")

            def worker():
                try:
                    results = self.application.import_eroscripts(url)
                    count = len(results) if results else 0
                    self.root.after(0, lambda: finish_import(count))
                except Exception as error:
                    self.root.after(0, lambda: fail_import(error))

            threading.Thread(target=worker, daemon=True).start()

        def finish_import(count):
            try:
                self.application.rebuild_library()
                self.application.build_index()
                self.refresh_count()
                self.set_status(f"Imported {count} funscript(s) from EroScripts.")
                window.destroy()
                messagebox.showinfo(
                    "Import Complete",
                    f"Imported: {count} funscript(s).\n\nLibrary and index.json were rebuilt.",
                    parent=self.root,
                )
            except Exception as error:
                fail_import(error)

        def fail_import(error):
            import_button.config(state="normal")
            url_entry.config(state="normal")
            url_status.set("Import failed.")
            self.set_status("EroScripts import failed")
            messagebox.showerror(
                "Import Funscript Failed",
                str(error),
                parent=window,
            )

        import_button.config(command=start_import)

    def add_local_funscripts(self):
        files = filedialog.askopenfilenames(
            parent=self.root,
            title="Select funscript files",
            filetypes=[("Funscript files", "*.funscript"), ("All files", "*.*")],
        )

        if not files:
            return

        destination = self.application.root / self.application.config.funscripts_dir
        destination.mkdir(parents=True, exist_ok=True)

        copied = 0
        skipped = 0

        try:
            for selected in files:
                source = Path(selected)
                target = destination / source.name

                if target.exists():
                    skipped += 1
                    continue

                shutil.copy2(source, target)
                copied += 1

            self.application.rebuild_library()
            self.application.build_index()
            self.refresh_count()
            self.set_status(f"Added {copied} file(s); skipped {skipped} existing file(s).")

            messagebox.showinfo(
                "Funscripts Added",
                f"Added: {copied}\nAlready present: {skipped}\n\nLibrary and index.json were rebuilt.",
                parent=self.root,
            )
        except Exception as error:
            self.set_status("Add failed")
            messagebox.showerror("Add Funscript Failed", str(error), parent=self.root)

    def rebuild_library(self):
        try:
            self.application.rebuild_library()
            self.refresh_count()
            self.set_status("Library rebuilt successfully.")
        except Exception as error:
            self.set_status("Library rebuild failed")
            messagebox.showerror("Rebuild Failed", str(error), parent=self.root)

    def build_index(self):
        try:
            self.application.build_index()
            self.set_status("index.json generated successfully.")
        except Exception as error:
            self.set_status("Index generation failed")
            messagebox.showerror("Build Index Failed", str(error), parent=self.root)

    def validate_library(self):
        try:
            self.application.validate_library()
            self.refresh_count()
            self.set_status("Library validation completed successfully.")
        except Exception as error:
            self.set_status("Validation failed")
            messagebox.showerror("Validation Failed", str(error), parent=self.root)

    def view_funscripts(self):
        window = tk.Toplevel(self.root)
        window.title("Funscript Library")
        window.geometry("760x520")
        window.minsize(620, 420)

        outer = ttk.Frame(window, padding=14)
        outer.pack(fill="both", expand=True)

        top = ttk.Frame(outer)
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        search = ttk.Entry(top, textvariable=search_var)
        search.pack(side="left", fill="x", expand=True, padx=(8, 0))

        columns = ("title", "creator", "site", "video_id")
        tree = ttk.Treeview(outer, columns=columns, show="headings", selectmode="browse")

        # Column sorting state.  Funscript is the default sort.
        sort_column = {"value": "title"}
        sort_reverse = {"value": False}

        def update_headings():
            labels = {
                "title": "Funscript",
                "creator": "Creator",
                "site": "Site",
                "video_id": "Video ID",
            }
            for column, label in labels.items():
                if column == sort_column["value"]:
                    arrow = " ▼" if sort_reverse["value"] else " ▲"
                    tree.heading(column, text=label + arrow)
                else:
                    tree.heading(column, text=label)

        def sort_by(column):
            if sort_column["value"] == column:
                sort_reverse["value"] = not sort_reverse["value"]
            else:
                sort_column["value"] = column
                sort_reverse["value"] = False
            update_headings()
            populate()

        tree.heading("title", text="Funscript", command=lambda: sort_by("title"))
        tree.heading("creator", text="Creator", command=lambda: sort_by("creator"))
        tree.heading("site", text="Site", command=lambda: sort_by("site"))
        tree.heading("video_id", text="Video ID", command=lambda: sort_by("video_id"))
        tree.column("title", width=310)
        tree.column("creator", width=130)
        tree.column("site", width=120)
        tree.column("video_id", width=100)

        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        scripts = []

        def load_scripts():
            scripts.clear()
            scripts.extend(self.application.database.all_scripts())
            populate()

        def populate(*_):
            query = search_var.get().strip().lower()
            tree.delete(*tree.get_children())

            rows = []

            for script in scripts:
                title = Path(script["filename"]).stem
                creator = script["creator"] or ""
                source = self.application.database.get_video_source(script["id"])
                site = source["site"] if source else ""
                video_id = source["video_id"] if source else ""

                haystack = f"{title} {script['filename']} {creator} {site} {video_id}".lower()
                if query and query not in haystack:
                    continue

                rows.append((script["id"], title, creator, site, video_id))

            index = {
                "title": 1,
                "creator": 2,
                "site": 3,
                "video_id": 4,
            }[sort_column["value"]]

            rows.sort(
                key=lambda row: str(row[index]).lower(),
                reverse=sort_reverse["value"],
            )

            for script_id, title, creator, site, video_id in rows:
                tree.insert(
                    "",
                    "end",
                    iid=str(script_id),
                    values=(title, creator, site, video_id),
                )

        search_var.trace_add("write", populate)
        ttk.Button(top, text="Refresh", command=load_scripts).pack(side="right", padx=(8, 0))

        update_headings()

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Close", command=window.destroy).pack(side="right")

        load_scripts()

    def show_settings(self):
        config = self.application.config
        messagebox.showinfo(
            "Settings",
            f"Database: {config.database}\n"
            f"Funscripts: {config.funscripts_dir}\n"
            f"Images: {config.images_dir}\n"
            f"Metadata: {config.metadata_dir}\n"
            f"Index: {config.index_file}\n"
            f"GitHub raw base: {getattr(config, 'raw_base_url', '')}",
            parent=self.root,
        )
