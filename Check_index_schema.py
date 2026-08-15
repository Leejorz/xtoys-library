import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

GENERATED_INDEX = PROJECT_ROOT / "index.json"
REFERENCE_INDEX = PROJECT_ROOT / "(example)index.json"


EXPECTED_TOP_LEVEL = {
    "author",
    "videos",
    "version",
    "tags",
}


EXPECTED_VIDEO_FIELDS = {
    "name",
    "site",
    "id",
    "scripts",
    "tags",
    "created_at",
    "url",
    "valid",
    "creator",
    "ignore",
    "last_checked",
    "thumbnail",
    "displayName",
}


EXPECTED_SCRIPT_FIELDS = {
    "name",
    "location",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def field_report(actual, expected, label):
    actual_fields = set(actual.keys())

    missing = expected - actual_fields
    extra = actual_fields - expected

    if missing:
        print(f"  MISSING {label} fields:")
        for field in sorted(missing):
            print(f"    - {field}")

    if extra:
        print(f"  EXTRA {label} fields:")
        for field in sorted(extra):
            print(f"    + {field}")

    if not missing and not extra:
        print(f"  {label} fields: OK")

    return not missing and not extra


def main():

    print("=" * 60)
    print("        xToys index.json Schema Diagnostic")
    print("=" * 60)

    print()
    print(f"Generated: {GENERATED_INDEX}")
    print(f"Reference: {REFERENCE_INDEX}")

    if not GENERATED_INDEX.exists():
        print("\nERROR: index.json does not exist.")
        return 1

    if not REFERENCE_INDEX.exists():
        print("\nERROR: (example)index.json does not exist.")
        print()
        print("Copy the reference file into the project root first.")
        return 1

    try:
        generated = load_json(GENERATED_INDEX)
        reference = load_json(REFERENCE_INDEX)
    except Exception as error:
        print(f"\nERROR: Could not read JSON: {error}")
        return 1

    errors = 0

    # ------------------------------------------------------------
    # Top level
    # ------------------------------------------------------------

    print("\n[1] TOP-LEVEL STRUCTURE")

    generated_top = set(generated.keys())
    reference_top = set(reference.keys())

    print("  Reference fields:")
    for field in sorted(reference_top):
        print(f"    - {field}")

    print("  Generated fields:")
    for field in sorted(generated_top):
        print(f"    - {field}")

    missing_top = reference_top - generated_top
    extra_top = generated_top - reference_top

    if missing_top:
        errors += 1
        print("\n  MISSING:")
        for field in sorted(missing_top):
            print(f"    - {field}")

    if extra_top:
        errors += 1
        print("\n  EXTRA:")
        for field in sorted(extra_top):
            print(f"    + {field}")

    if not missing_top and not extra_top:
        print("\n  TOP-LEVEL STRUCTURE: OK")

    # ------------------------------------------------------------
    # Top-level types
    # ------------------------------------------------------------

    print("\n[2] TOP-LEVEL TYPES")

    type_checks = {
        "author": str,
        "videos": list,
        "version": int,
        "tags": dict,
    }

    for field, expected_type in type_checks.items():

        value = generated.get(field)

        if not isinstance(value, expected_type):
            errors += 1
            print(
                f"  ERROR: {field} should be "
                f"{expected_type.__name__}, got "
                f"{type(value).__name__}"
            )
        else:
            print(
                f"  {field}: OK "
                f"({expected_type.__name__})"
            )

    # ------------------------------------------------------------
    # Video structure
    # ------------------------------------------------------------

    print("\n[3] VIDEO OBJECT STRUCTURE")

    videos = generated.get("videos", [])

    print(
        f"  Generated video objects: {len(videos)}"
    )

    if not videos:
        errors += 1
        print("  ERROR: No video objects found.")

    for index, video in enumerate(videos, start=1):

        label = f"Video #{index}"

        if not isinstance(video, dict):
            errors += 1
            print(
                f"  ERROR: {label} is not an object."
            )
            continue

        if not field_report(
            video,
            EXPECTED_VIDEO_FIELDS,
            label
        ):
            errors += 1

    # ------------------------------------------------------------
    # Nested scripts
    # ------------------------------------------------------------

    print("\n[4] NESTED SCRIPT STRUCTURE")

    total_scripts = 0

    for index, video in enumerate(videos, start=1):

        scripts = video.get("scripts")

        if not isinstance(scripts, list):
            errors += 1
            print(
                f"  ERROR: Video #{index} scripts "
                f"is not an array."
            )
            continue

        if not scripts:
            errors += 1
            print(
                f"  ERROR: Video #{index} "
                f"contains no scripts."
            )
            continue

        for script_index, script in enumerate(
            scripts,
            start=1
        ):

            total_scripts += 1

            label = (
                f"Video #{index} "
                f"Script #{script_index}"
            )

            if not isinstance(script, dict):
                errors += 1
                print(
                    f"  ERROR: {label} "
                    f"is not an object."
                )
                continue

            if not field_report(
                script,
                EXPECTED_SCRIPT_FIELDS,
                label
            ):
                errors += 1

    print(
        f"  Total nested scripts: {total_scripts}"
    )

    # ------------------------------------------------------------
    # Required value sanity checks
    # ------------------------------------------------------------

    print("\n[5] REQUIRED VALUE CHECKS")

    for index, video in enumerate(videos, start=1):

        name = video.get("name")
        display_name = video.get("displayName")

        if not name:
            errors += 1
            print(
                f"  ERROR: Video #{index} "
                f"has empty name."
            )

        if not display_name:
            errors += 1
            print(
                f"  ERROR: Video #{index} "
                f"has empty displayName."
            )

        if name != display_name:
            errors += 1
            print(
                f"  ERROR: Video #{index} "
                f"name/displayName mismatch:"
            )
            print(f"    name        = {name!r}")
            print(
                f"    displayName = "
                f"{display_name!r}"
            )

        scripts = video.get("scripts", [])

        for script in scripts:

            if not script.get("name"):
                errors += 1
                print(
                    f"  ERROR: {name}: "
                    f"script has empty name."
                )

            if not script.get("location"):
                errors += 1
                print(
                    f"  ERROR: {name}: "
                    f"script has empty location."
                )

    # ------------------------------------------------------------
    # Reference comparison
    # ------------------------------------------------------------

    print("\n[6] REFERENCE SCHEMA COMPARISON")

    reference_videos = reference.get(
        "videos",
        []
    )

    if reference_videos:

        reference_video = reference_videos[0]

        print(
            "  Reference video fields:"
        )

        for field in sorted(
            reference_video.keys()
        ):
            print(f"    - {field}")

        reference_scripts = reference_video.get(
            "scripts",
            []
        )

        if reference_scripts:

            print(
                "\n  Reference script fields:"
            )

            for field in sorted(
                reference_scripts[0].keys()
            ):
                print(f"    - {field}")

    # ------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------

    print()
    print("=" * 60)

    if errors:
        print(
            f"SCHEMA CHECK FAILED "
            f"({errors} problem(s))"
        )
        print("=" * 60)
        return 1

    print("SCHEMA CHECK PASSED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())