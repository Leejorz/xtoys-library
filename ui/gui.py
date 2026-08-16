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
        self._button(actions, "Publish to GitHub", self.publish_to_github, 2, 1)
        self._button(actions, "Settings", self.show_settings, 3, 0)

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
        """Import EroScripts through a small multi-page GUI wizard."""
        window = tk.Toplevel(self.root)
        window.title("Add Funscript")
        window.geometry("700x500")
        window.minsize(640, 440)
        window.transient(self.root)
        window.grab_set()

        container = ttk.Frame(window, padding=20)
        container.pack(fill="both", expand=True)

        pages = {}
        current_page = {"value": None}
        results_holder = {"value": []}
        missing_holder = {"value": []}
        eroscripts_url_holder = {"value": ""}
        fallback_vars = {}

        def show_page(name):
            for frame in pages.values():
                frame.pack_forget()
            pages[name].pack(fill="both", expand=True)
            current_page["value"] = name

        def add_page(name):
            frame = ttk.Frame(container)
            pages[name] = frame
            return frame

        # ------------------------------------------------------------
        # Page 1: EroScripts URL
        # ------------------------------------------------------------
        page1 = add_page("input")
        ttk.Label(page1, text="Add Funscript", font=("TkDefaultFont", 16, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            page1,
            text="Enter the EroScripts page URL. The app will download the funscript and attempt to detect its video source automatically.",
            wraplength=640,
        ).pack(anchor="w", pady=(0, 18))

        url_frame = ttk.LabelFrame(page1, text="EroScripts page", padding=12)
        url_frame.pack(fill="x", pady=(0, 18))
        url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=url_var)
        url_entry.pack(fill="x")

        page1_status = tk.StringVar(value="")
        ttk.Label(page1, textvariable=page1_status).pack(anchor="w", pady=(0, 12))

        page1_buttons = ttk.Frame(page1)
        page1_buttons.pack(fill="x", side="bottom")
        ttk.Button(page1_buttons, text="Import", command=lambda: start_import()).pack(side="left")
        ttk.Button(
            page1_buttons,
            text="Choose Local Funscript Files",
            command=lambda: (window.destroy(), self.add_local_funscripts()),
        ).pack(side="left", padx=(10, 0))
        ttk.Button(page1_buttons, text="Cancel", command=window.destroy).pack(side="right")

        # ------------------------------------------------------------
        # Page 2: Download + automatic detection
        # ------------------------------------------------------------
        page2 = add_page("detect")
        ttk.Label(page2, text="Download & Detect", font=("TkDefaultFont", 16, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            page2,
            text="The funscript is downloaded first. The app then automatically checks the EroScripts page for the video site and video ID.",
            wraplength=640,
        ).pack(anchor="w", pady=(0, 14))

        detection_status = tk.StringVar(value="Starting import...")
        ttk.Label(page2, textvariable=detection_status, wraplength=640).pack(anchor="w", pady=(0, 12))

        detection_frame = ttk.LabelFrame(page2, text="Automatic detection", padding=10)
        detection_frame.pack(fill="both", expand=True, pady=(0, 14))

        detection_tree = ttk.Treeview(
            detection_frame,
            columns=("funscript", "site", "video_id", "status"),
            show="headings",
            height=10,
        )
        for column, heading, width in (
            ("funscript", "Funscript", 250),
            ("site", "Site", 130),
            ("video_id", "Video ID", 130),
            ("status", "Status", 110),
        ):
            detection_tree.heading(column, text=heading)
            detection_tree.column(column, width=width, anchor="w")
        detection_tree.pack(fill="both", expand=True)

        page2_status = tk.StringVar(value="")
        ttk.Label(page2, textvariable=page2_status).pack(anchor="w", pady=(0, 10))
        page2_buttons = ttk.Frame(page2)
        page2_buttons.pack(fill="x", side="bottom")
        detect_next_button = ttk.Button(page2_buttons, text="Continue", state="disabled")
        detect_next_button.pack(side="left")
        ttk.Button(page2_buttons, text="Cancel", command=window.destroy).pack(side="right")

        # ------------------------------------------------------------
        # Page 3: fallback source selection
        # ------------------------------------------------------------
        page3 = add_page("fallback")
        ttk.Label(page3, text="Video Source", font=("TkDefaultFont", 16, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            page3,
            text="Automatic detection could not determine a supported video source for the item(s) below. Enter a source URL, or use the placeholder.",
            wraplength=640,
        ).pack(anchor="w", pady=(0, 14))

        fallback_frame = ttk.Frame(page3)
        fallback_frame.pack(fill="both", expand=True)

        page3_status = tk.StringVar(value="")
        ttk.Label(page3, textvariable=page3_status, wraplength=640).pack(anchor="w", pady=(10, 10))
        page3_buttons = ttk.Frame(page3)
        page3_buttons.pack(fill="x", side="bottom")
        fallback_save_button = ttk.Button(page3_buttons, text="Continue to Save")
        fallback_save_button.pack(side="left")
        ttk.Button(page3_buttons, text="Cancel", command=window.destroy).pack(side="right")

        # ------------------------------------------------------------
        # Page 4: review + save
        # ------------------------------------------------------------
        page4 = add_page("save")
        ttk.Label(page4, text="Save", font=("TkDefaultFont", 16, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            page4,
            text="Review the detected video source information, then save the import to the library.",
            wraplength=640,
        ).pack(anchor="w", pady=(0, 14))

        save_frame = ttk.LabelFrame(page4, text="Import summary", padding=10)
        save_frame.pack(fill="both", expand=True, pady=(0, 14))
        save_text = tk.Text(save_frame, height=12, wrap="word", state="disabled")
        save_text.pack(fill="both", expand=True)

        save_status = tk.StringVar(value="")
        ttk.Label(page4, textvariable=save_status, wraplength=640).pack(anchor="w", pady=(0, 10))
        page4_buttons = ttk.Frame(page4)
        page4_buttons.pack(fill="x", side="bottom")
        save_button = ttk.Button(page4_buttons, text="Save to Library")
        save_button.pack(side="left")
        ttk.Button(page4_buttons, text="Cancel", command=window.destroy).pack(side="right")

        def populate_detection_page(results):
            for item in detection_tree.get_children():
                detection_tree.delete(item)

            missing = []
            for result in results:
                site = getattr(result, "video_site", None) or ""
                video_id = getattr(result, "video_id", None) or ""
                if site and video_id:
                    status = "Detected"
                else:
                    status = "Needs source"
                    missing.append(result)
                detection_tree.insert("", "end", values=(result.filename, site or "—", video_id or "—", status))

            missing_holder["value"] = missing
            if missing:
                detection_status.set("Automatic detection finished. Some video sources need your input.")
                page2_status.set(f"{len(missing)} funscript(s) need a video source.")
                detect_next_button.config(state="normal", command=lambda: show_fallback_page(missing))
            else:
                detection_status.set("Automatic detection succeeded for all imported funscripts.")
                page2_status.set("All video sources detected automatically. Opening Save...")
                detect_next_button.config(state="disabled")
                # Give the user a moment to see the detected site/ID before
                # moving to the final Save page.
                self.root.after(650, show_save_page)

        def show_fallback_page(missing):
            for child in fallback_frame.winfo_children():
                child.destroy()
            fallback_vars.clear()

            for index, result in enumerate(missing):
                box = ttk.LabelFrame(fallback_frame, text=result.filename, padding=10)
                box.pack(fill="x", pady=(0, 10))

                var = tk.StringVar()
                fallback_vars[id(result)] = var
                ttk.Label(box, text="Video Source URL:").pack(anchor="w")
                entry_row = ttk.Frame(box)
                entry_row.pack(fill="x", pady=(5, 5))
                entry = ttk.Entry(entry_row, textvariable=var)
                entry.pack(side="left", fill="x", expand=True)

                detected_var = tk.StringVar(value="Not detected")
                ttk.Label(box, textvariable=detected_var).pack(anchor="w")

                def on_change(_event=None, value_var=var, display_var=detected_var):
                    value = value_var.get().strip()
                    candidate = self.application.detect_video_source(value) if value else None
                    if candidate:
                        display_var.set(f"Detected: {candidate['site']} | Video ID: {candidate['video_id']}")
                    elif value:
                        display_var.set("Could not detect a supported site / video ID")
                    else:
                        display_var.set("Not detected")

                entry.bind("<KeyRelease>", on_change)

                ttk.Button(
                    entry_row,
                    text="Use Placeholder",
                    command=lambda r=result, v=var, d=detected_var: (
                        v.set(""),
                        self.application.apply_placeholder_video_source(r),
                        d.set("Placeholder source selected"),
                    ),
                ).pack(side="left", padx=(8, 0))

            page3_status.set("Enter a supported video URL for each item, or select Use Placeholder.")
            show_page("fallback")

        def apply_fallback_sources():
            unresolved = []
            for result in missing_holder["value"]:
                # If a placeholder was selected, video_site is already populated.
                if getattr(result, "video_site", None) and getattr(result, "video_id", None):
                    continue
                value = fallback_vars.get(id(result), tk.StringVar()).get().strip()
                candidate = self.application.detect_video_source(value) if value else None
                if candidate:
                    self.application.apply_detected_video_source(result, candidate)
                else:
                    unresolved.append(result.filename)

            if unresolved:
                messagebox.showwarning(
                    "Video Source Required",
                    "Please enter a supported video URL or choose Use Placeholder for:\n\n" + "\n".join(unresolved),
                    parent=window,
                )
                return
            show_save_page()

        fallback_save_button.config(command=apply_fallback_sources)

        def show_save_page():
            for result in results_holder["value"]:
                if not getattr(result, "video_site", None) or not getattr(result, "video_id", None):
                    return

            save_text.config(state="normal")
            save_text.delete("1.0", "end")
            for result in results_holder["value"]:
                save_text.insert(
                    "end",
                    f"Funscript: {result.filename}\n"
                    f"Creator: {result.creator or '—'}\n"
                    f"Site: {result.video_site or '—'}\n"
                    f"Video ID: {result.video_id or '—'}\n"
                    f"Source URL: {result.video_url or '—'}\n\n",
                )
            save_text.config(state="disabled")
            save_status.set(f"Ready to save {len(results_holder['value'])} funscript(s).")
            show_page("save")

        def save_import():
            save_button.config(state="disabled")
            save_status.set("Saving to SQLite and rebuilding the library...")
            self.set_status("Saving EroScripts import...")

            try:
                # IMPORTANT: database work is intentionally performed on the
                # Tkinter/main thread. The background worker only uses
                # Playwright and returns plain result objects.
                for result in results_holder["value"]:
                    self.application.save_eroscripts_import(
                        result,
                        eroscripts_url_holder["value"],
                    )

                self.application.rebuild_library()
                self.application.build_index()
                self.refresh_count()
                self.set_status(
                    f"Imported {len(results_holder['value'])} funscript(s) from EroScripts."
                )
                window.destroy()
                messagebox.showinfo(
                    "Import Complete",
                    f"Imported: {len(results_holder['value'])} funscript(s).\n\nLibrary and index.json were rebuilt.",
                    parent=self.root,
                )
            except Exception as error:
                save_button.config(state="normal")
                save_status.set("Save failed.")
                self.set_status("EroScripts save failed")
                messagebox.showerror("Save Import Failed", str(error), parent=window)

        save_button.config(command=save_import)

        def start_import():
            url = url_var.get().strip()
            if not url:
                messagebox.showwarning("EroScripts URL Required", "Paste an EroScripts page URL first.", parent=window)
                return

            eroscripts_url_holder["value"] = url
            page1_status.set("Starting...")
            show_page("detect")
            detection_status.set("Downloading funscript(s) from EroScripts...")
            page2_status.set("The browser/importer is working. Please wait.")
            detect_next_button.config(state="disabled")

            def worker():
                try:
                    results = self.application.import_eroscripts(
                        url,
                        video_source_url=None,
                        interactive=False,
                        persist=False,
                    )
                    # Source detection here is memory-only. No SQLite access.
                    for result in results:
                        self.application.prepare_video_source(result)
                    self.root.after(0, lambda results=results: import_finished(results))
                except Exception as error:
                    self.root.after(0, lambda error=error: import_failed(error))

            threading.Thread(target=worker, daemon=True).start()

        def import_finished(results):
            results_holder["value"] = results or []
            if not results_holder["value"]:
                import_failed(RuntimeError("EroScripts did not return any funscript files."))
                return
            populate_detection_page(results_holder["value"])

        def import_failed(error):
            self.set_status("EroScripts import failed")
            messagebox.showerror("Import Funscript Failed", str(error), parent=window)
            show_page("input")
            page1_status.set("Import failed. Please check the URL/session and try again.")

        url_entry.focus_set()
        show_page("input")

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

    def publish_to_github(self):
        """Open the GitHub publisher and safely report any GUI callback error."""
        self.set_status("Opening GitHub publisher...")
        try:
            self._open_github_publish_dialog()
        except Exception as error:
            self.set_status("GitHub publisher failed to open")
            messagebox.showerror("GitHub Publisher", str(error), parent=self.root)

    def _open_github_publish_dialog(self):
        """Rebuild, validate, then commit and push the current library."""
        commit_message = tk.StringVar(value="Update xToys Library")

        dialog = tk.Toplevel(self.root)
        dialog.title("Publish to GitHub")
        dialog.geometry("620x430")
        dialog.minsize(560, 380)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Publish Library to GitHub",
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            frame,
            text=(
                "The app will rebuild the library, regenerate index.json, "
                "validate it against the example schema, then commit and "
                "push the changes to origin/main."
            ),
            wraplength=570,
        ).pack(anchor="w", pady=(0, 12))

        message_frame = ttk.LabelFrame(frame, text="Commit message", padding=10)
        message_frame.pack(fill="x", pady=(0, 12))
        ttk.Entry(message_frame, textvariable=commit_message).pack(fill="x")

        log_frame = ttk.LabelFrame(frame, text="Publish progress", padding=8)
        log_frame.pack(fill="both", expand=True, pady=(0, 12))
        log = tk.Text(log_frame, height=12, wrap="word", state="disabled")
        log.pack(fill="both", expand=True)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        publish_button = ttk.Button(buttons, text="Publish")
        publish_button.pack(side="left")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")

        def append_log(text):
            log.config(state="normal")
            log.insert("end", text + "\n")
            log.see("end")
            log.config(state="disabled")
            self.root.update_idletasks()

        def finish_success(result):
            publish_button.config(state="normal")
            append_log("")
            if not result.get("changed"):
                append_log(result["message"])
                self.set_status("GitHub already up to date.")
                messagebox.showinfo("GitHub Publish", result["message"], parent=dialog)
                return

            append_log(f"Commit: {result['commit']}")
            append_log("Push completed successfully.")
            self.set_status("Published library to GitHub successfully.")
            messagebox.showinfo(
                "Publish Complete",
                f"Published successfully.\n\nCommit: {result['commit']}\nRemote: {result['remote']}",
                parent=dialog,
            )
            dialog.destroy()

        def finish_error(error):
            publish_button.config(state="normal")
            append_log(f"ERROR: {error}")
            self.set_status("GitHub publish failed")
            messagebox.showerror("GitHub Publish Failed", str(error), parent=dialog)

        def start_publish():
            message = commit_message.get().strip()
            if not message:
                messagebox.showwarning("Commit Message", "Enter a commit message first.", parent=dialog)
                return

            publish_button.config(state="disabled")
            append_log("Rebuilding library...")
            self.set_status("Preparing GitHub publish...")

            try:
                self.application.rebuild_library()
                self.application.build_index()
                self.refresh_count()
            except Exception as error:
                finish_error(error)
                return

            append_log("Library rebuilt and index.json generated.")
            append_log("Validating index.json against (example)index.json...")

            def worker():
                try:
                    valid, output = self.application.validate_index_schema()
                    if output:
                        tail = output[-1800:]
                        self.root.after(0, lambda tail=tail: append_log(tail))
                    if not valid:
                        raise RuntimeError("index.json schema validation failed. Nothing was pushed.")

                    preview = self.application.git_publish_preview()
                    self.root.after(0, lambda: append_log("Schema validation passed."))
                    self.root.after(0, lambda preview=preview: append_log(
                        f"Target: {preview['remote']} (branch: {preview['branch']})"
                    ))
                    self.root.after(0, lambda preview=preview: append_log(
                        "Changes ready to publish: " + str(len(preview['files']))
                    ))
                    for changed in preview["files"]:
                        self.root.after(0, lambda changed=changed: append_log(f"  {changed}"))

                    def confirm_and_push():
                        if not messagebox.askyesno(
                            "Confirm Publish",
                            f"Publish {len(preview['files'])} change(s) to GitHub?\n\n{preview['remote']}",
                            parent=dialog,
                        ):
                            publish_button.config(state="normal")
                            append_log("Publish cancelled. No commit or push was made.")
                            self.set_status("GitHub publish cancelled.")
                            return

                        append_log("Staging, committing, and pushing to GitHub...")

                        def push_worker():
                            try:
                                result = self.application.git_publish(message)
                                self.root.after(0, lambda result=result: finish_success(result))
                            except Exception as error:
                                self.root.after(0, lambda error=error: finish_error(error))

                        threading.Thread(target=push_worker, daemon=True).start()

                    self.root.after(0, confirm_and_push)
                except Exception as error:
                    self.root.after(0, lambda error=error: finish_error(error))

            threading.Thread(target=worker, daemon=True).start()

        publish_button.config(command=start_publish)

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

        # ---------------------------------------------------------
        # Video source management
        #
        # Double-clicking a funscript, or using Edit Video Source,
        # opens a small editor.  The source URL is the authoritative
        # input: the application detects the supported site and video
        # ID from it automatically.
        # ---------------------------------------------------------

        def edit_selected_source(event=None):
            selection = tree.selection()

            if not selection:
                messagebox.showinfo(
                    "Select Funscript",
                    "Select a funscript first.",
                    parent=window,
                )
                return

            script_id = int(selection[0])

            try:
                script = next(
                    item for item in scripts
                    if item["id"] == script_id
                )
            except StopIteration:
                messagebox.showerror(
                    "Video Source",
                    "The selected funscript could not be found.",
                    parent=window,
                )
                return

            source = self.application.database.get_video_source(
                script_id
            )

            editor = tk.Toplevel(window)
            editor.title("Edit Video Source")
            editor.geometry("620x330")
            editor.minsize(560, 300)
            editor.transient(window)
            editor.grab_set()

            frame = ttk.Frame(editor, padding=14)
            frame.pack(fill="both", expand=True)

            title = Path(script["filename"]).stem

            ttk.Label(
                frame,
                text=title,
                font=("TkDefaultFont", 14, "bold"),
            ).pack(anchor="w", pady=(0, 12))

            ttk.Label(
                frame,
                text=(
                    "Paste the video URL below. The supported site and "
                    "video ID will be detected automatically."
                ),
                wraplength=570,
            ).pack(anchor="w", pady=(0, 12))

            url_var = tk.StringVar(
                value=(
                    source["source_url"]
                    if source and source["source_url"]
                    else ""
                )
            )
            site_var = tk.StringVar(
                value=(
                    source["site"]
                    if source and source["site"]
                    else ""
                )
            )
            id_var = tk.StringVar(
                value=(
                    source["video_id"]
                    if source and source["video_id"]
                    else ""
                )
            )
            status_var = tk.StringVar(value="")

            url_frame = ttk.LabelFrame(
                frame,
                text="Video Source URL",
                padding=10,
            )
            url_frame.pack(fill="x", pady=(0, 10))

            url_entry = ttk.Entry(
                url_frame,
                textvariable=url_var,
            )
            url_entry.pack(fill="x")

            detected = ttk.Frame(frame)
            detected.pack(fill="x", pady=(0, 10))

            ttk.Label(
                detected,
                text="Site:",
            ).grid(row=0, column=0, sticky="w", padx=(0, 8))

            site_entry = ttk.Entry(
                detected,
                textvariable=site_var,
                state="readonly",
                width=28,
            )
            site_entry.grid(row=0, column=1, sticky="ew", padx=(0, 18))

            ttk.Label(
                detected,
                text="Video ID:",
            ).grid(row=0, column=2, sticky="w", padx=(0, 8))

            id_entry = ttk.Entry(
                detected,
                textvariable=id_var,
                state="readonly",
                width=18,
            )
            id_entry.grid(row=0, column=3, sticky="ew")

            detected.columnconfigure(1, weight=1)
            detected.columnconfigure(3, weight=1)

            ttk.Label(
                frame,
                textvariable=status_var,
                wraplength=570,
            ).pack(anchor="w", pady=(0, 10))

            buttons = ttk.Frame(frame)
            buttons.pack(fill="x", side="bottom")

            def detect_source():
                url = url_var.get().strip()

                if not url:
                    site_var.set("")
                    id_var.set("")
                    status_var.set(
                        "Enter a video URL first."
                    )
                    return

                try:
                    detected_source = (
                        self.application.detect_video_source(
                            url
                        )
                    )
                except Exception as error:
                    detected_source = None
                    status_var.set(
                        f"Detection failed: {error}"
                    )
                    return

                if detected_source is None:
                    site_var.set("")
                    id_var.set("")
                    status_var.set(
                        "That URL is not a supported xToys video source, "
                        "or its video ID could not be detected."
                    )
                    return

                site_var.set(
                    detected_source["site"]
                )
                id_var.set(
                    detected_source["video_id"]
                )
                url_var.set(
                    detected_source["url"]
                )
                status_var.set(
                    "Video source detected successfully."
                )

            def use_placeholder():
                site_var.set(
                    self.application.PLACEHOLDER_VIDEO_SITE
                )
                id_var.set(
                    self.application.PLACEHOLDER_VIDEO_ID
                )
                url_var.set(
                    self.application.PLACEHOLDER_VIDEO_URL
                )
                status_var.set(
                    "Placeholder video source selected."
                )

            def save_source():
                url = url_var.get().strip()
                site = site_var.get().strip()
                video_id = id_var.get().strip()

                if not url or not site or not video_id:
                    messagebox.showwarning(
                        "Video Source Required",
                        "Enter a supported video URL and detect the "
                        "site and video ID, or choose Use Placeholder.",
                        parent=editor,
                    )
                    return

                try:
                    if source:
                        self.application.database.edit_video_source(
                            source["id"],
                            site=site,
                            video_id=video_id,
                            source_url=url,
                        )
                    else:
                        self.application.database.upsert_video_source(
                            script_id=script_id,
                            site=site,
                            video_id=video_id,
                            source_url=url,
                        )

                    self.application.build_index()

                    editor.destroy()
                    load_scripts()
                    self.refresh_count()
                    self.set_status(
                        f"Video source saved for {title}."
                    )

                except Exception as error:
                    messagebox.showerror(
                        "Save Video Source Failed",
                        str(error),
                        parent=editor,
                    )

            ttk.Button(
                buttons,
                text="Detect",
                command=detect_source,
            ).pack(side="left")

            ttk.Button(
                buttons,
                text="Use Placeholder",
                command=use_placeholder,
            ).pack(side="left", padx=(8, 0))

            ttk.Button(
                buttons,
                text="Save",
                command=save_source,
            ).pack(side="right")

            ttk.Button(
                buttons,
                text="Cancel",
                command=editor.destroy,
            ).pack(side="right", padx=(0, 8))

            url_entry.focus_set()

        tree.bind(
            "<Double-1>",
            edit_selected_source
        )

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(10, 0))

        ttk.Button(
            bottom,
            text="Edit Video Source",
            command=edit_selected_source,
        ).pack(side="left")

        ttk.Button(
            bottom,
            text="Close",
            command=window.destroy,
        ).pack(side="right")

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
