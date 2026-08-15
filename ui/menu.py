class MainMenu:

    def __init__(self, application):
        self.application = application

    def run(self):

        while True:

            print("\n" + "=" * 41)
            print("        xToys Library Manager")
            print("=" * 41)

            print("1. Add Script from EroScripts URL")
            print("2. Rebuild Library")
            print("3. Build index.json")
            print("4. Edit Video Source")
            print("5. Validate Library")
            print("6. Sync GitHub")
            print("7. Settings")
            print("8. Exit")

            print()

            choice = input("Choice: ").strip()

            if choice == "1":

                self.add_from_eroscripts()

            elif choice == "2":

                self.application.rebuild_library()

            elif choice == "3":

                self.application.build_index()

            elif choice == "4":

                self.edit_video_source()

            elif choice == "5":

                try:

                    self.application.validate_library()

                except Exception as error:

                    print(
                        "\nLibrary validation/cleanup failed:"
                    )

                    print(
                        f"  {error}"
                    )

            elif choice == "6":

                print(
                    "\nThat feature is scheduled "
                    "for a later milestone."
                )

            elif choice == "7":

                self.show_settings()

            elif choice == "8":

                print("\nGoodbye.")
                return

            else:

                print(
                    "\nPlease choose an option "
                    "from 1 to 8."
                )

    def edit_video_source(self):

        scripts = []

        for script in self.application.database.all_scripts():

            source = (
                self.application.database.get_video_source(
                    script["id"]
                )
            )

            if source is not None:
                scripts.append(
                    (
                        script,
                        source
                    )
                )

        if not scripts:

            print(
                "\nNo video sources found."
            )

            return

        print("\nAvailable video sources:\n")

        for index, (script, source) in enumerate(
            scripts,
            start=1
        ):

            print(
                f"{index}. "
                f"[script {script['id']}] "
                f"{script['title'] or script['filename']}"
            )

            print(
                f"   Site: {source['site']}"
            )

            print(
                f"   Video ID: {source['video_id']}"
            )

            if source["source_url"]:

                print(
                    f"   URL: {source['source_url']}"
                )

        print()

        selection = input(
            "Select source number (or press Enter to cancel): "
        ).strip()

        if not selection:

            return

        try:

            selection_index = int(
                selection
            )

        except ValueError:

            print(
                "\nPlease enter a valid number."
            )

            return

        if not 1 <= selection_index <= len(scripts):

            print(
                "\nSelection out of range."
            )

            return

        script, source = scripts[
            selection_index - 1
        ]

        print(
            "\nEditing video source:"
        )

        print(
            f"  Script ID: {script['id']}"
        )

        print(
            f"  Title:     "
            f"{script['title'] or script['filename']}"
        )

        print(
            f"  Source ID: {source['id']}"
        )

        print(
            f"  Current site:     {source['site']}"
        )

        print(
            f"  Current video ID: {source['video_id']}"
        )

        print(
            f"  Current URL:      "
            f"{source['source_url'] or ''}"
        )

        print(
            "\nEnter new values."
        )

        site = input(
            f"Site [{source['site']}]: "
        ).strip()

        if not site:

            site = source["site"]

        video_id = input(
            f"Video ID [{source['video_id']}]: "
        ).strip()

        if not video_id:

            video_id = source["video_id"]

        source_url = input(
            f"Source URL "
            f"[{source['source_url'] or ''}]: "
        ).strip()

        if not source_url:

            source_url = source["source_url"] or ""

        try:

            self.application.edit_video_source(
                source_id=source["id"],
                site=site,
                video_id=video_id,
                source_url=source_url
            )

            print(
                "\nVideo source updated successfully."
            )

            print(
                f"  Site:     {site}"
            )

            print(
                f"  Video ID: {video_id}"
            )

            print(
                f"  URL:      {source_url}"
            )

        except Exception as error:

            print(
                "\nVideo source update failed:"
            )

            print(
                f"  {error}"
            )

    def add_from_eroscripts(self):

        url = input(
            "\nEroScripts URL: "
        ).strip()

        if not url:

            print(
                "\nNo URL entered."
            )

            return

        try:

            result = self.application.import_eroscripts(
                url
            )

            print(
                "\nDownload successful."
            )

            print(
                f"Title:   {result.title}"
            )

            print(
                f"File:    {result.filename}"
            )

            print(
                f"Creator: {result.creator or 'Unknown'}"
            )

            if result.tags:

                print(
                    f"Tags:    {', '.join(result.tags)}"
                )

            else:

                print(
                    "Tags:    None found"
                )

            if result.video_site:

                print(
                    f"Video:   {result.video_site}"
                )

            else:

                print(
                    "Video:   None found"
                )

            if result.video_title:

                print(
                    f"Video title: {result.video_title}"
                )

            if result.video_url:

                print(
                    f"Video URL:   {result.video_url}"
                )

            if result.duration:

                print(
                    f"Length:  {result.duration}"
                )

            if result.average_speed is not None:

                print(
                    f"Speed:   {result.average_speed}"
                )

            if result.action_count is not None:

                print(
                    f"Actions: {result.action_count}"
                )

            print(
                f"SHA256:  {result.content_hash}"
            )

            print(
                f"Size:    {result.file_size} bytes"
            )

        except Exception as error:

            print(
                "\nImport failed:"
            )

            print(
                f"  {error}"
            )

    def show_settings(self):

        while True:

            print("\n" + "=" * 41)
            print("              Settings")
            print("=" * 41)

            print("1. EroScripts Login")
            print("2. View Configuration")
            print("3. Back")

            print()

            choice = input("Choice: ").strip()

            if choice == "1":

                try:

                    self.application.login_eroscripts()

                except Exception as error:

                    print(
                        "\nEroScripts login failed:"
                    )

                    print(
                        f"  {error}"
                    )

            elif choice == "2":

                config = self.application.config

                print("\nCurrent settings:")

                print(
                    f"  Database:   {config.database}"
                )

                print(
                    f"  Funscripts: {config.funscripts_dir}"
                )

                print(
                    f"  Images:     {config.images_dir}"
                )

                print(
                    f"  Metadata:   {config.metadata_dir}"
                )

                print(
                    f"  Index:      {config.index_file}"
                )

            elif choice == "3":

                return

            else:

                print(
                    "\nPlease choose 1, 2, or 3."
                )