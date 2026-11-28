"""Retention overlay: injects missing fields into upstream files after patch application."""
import sys
from pathlib import Path

# --- SettingsValues.kt: the SignalStore.settings object ---
SETTINGS_FILE = "app/src/main/java/org/thoughtcrime/securesms/keyvalue/SettingsValues.kt"

SETTINGS_PROPS = [
    ("KEEP_VIEW_ONCE_MESSAGES", "settings.keepViewOnceMessages", "isKeepViewOnceMessages", "true"),
    ("KEEP_EXPIRING_MESSAGES", "settings.keepExpiringMessages", "isKeepExpiringMessages", "true"),
    ("IGNORE_REMOTE_DELETE", "settings.ignoreRemoteDelete", "isIgnoreRemoteDelete", "true"),
    ("DELETE_MEDIA_ONLY", "settings.deleteMediaOnly", "isDeleteMediaOnly", "false"),
]

# Pre-built lookup: var_name -> const_name
VAR_TO_CONST = {v[2]: v[0] for v in SETTINGS_PROPS}

# --- ChatsSettingsState.kt: UI state data class ---
STATE_FILE = "feature/app-settings/src/main/java/org/signal/appsettings/chats/ChatsSettingsState.kt"

STATE_FIELDS = [
    "  ,\n",
    "  val keepExpiringMessages: Boolean = false,\n",
    "  val keepViewOnceMessages: Boolean = false,\n",
    "  val ignoreRemoteDelete: Boolean = false,\n",
    "  val deleteMediaOnly: Boolean = false\n",
]


def inject_settings():
    path = Path(SETTINGS_FILE)
    if not path.exists():
        print(f"::warning:: {SETTINGS_FILE} not found. Skipping.")
        return

    content = path.read_text(encoding="utf-8")

    # Idempotency
    if all(var in content for _, _, var, _ in SETTINGS_PROPS):
        print("SettingsValues.kt: all retention properties already present. Skipping.")
        return

    modified = False

    # 1. Inject companion object constants
    anchor = 'private const val AUTOPLAY_STICKERS_AND_GIFS = "settings.chats.autoplayStickersAndGifs"'
    if anchor not in content:
        anchor = "const val BACKUP_DEFAULT_HOUR = 2"
        if anchor not in content:
            print("::error:: Could not find anchor in SettingsValues.kt")
            sys.exit(1)
        # Insert before anchor (reverse order so final order matches SETTINGS_PROPS)
        for const_name, const_value, _, _ in reversed(SETTINGS_PROPS):
            if const_name not in content:
                line = f'    private const val {const_name} = "{const_value}"\n'
                content = content.replace(anchor, line + "    " + anchor, 1)
                modified = True
    else:
        # Insert after anchor (forward order)
        for const_name, const_value, _, _ in SETTINGS_PROPS:
            if const_name not in content:
                line = f'\n    private const val {const_name} = "{const_value}"'
                content = content.replace(anchor, anchor + line, 1)
                modified = True

    # 2. Inject var declarations
    var_anchor = "var isAutoplayStickersAndGifsEnabled: Boolean by booleanValue(AUTOPLAY_STICKERS_AND_GIFS, true)"
    if var_anchor not in content:
        var_anchor = "var keepMessagesDuration: KeepMessagesDuration"
        if var_anchor not in content:
            print("::error:: Could not find var anchor in SettingsValues.kt")
            sys.exit(1)
        # Insert before anchor (reverse order so final order matches SETTINGS_PROPS)
        for _, _, var_name, default in reversed(SETTINGS_PROPS):
            if var_name not in content:
                line = f"  var {var_name}: Boolean by booleanValue({VAR_TO_CONST[var_name]}, {default})\n\n  "
                content = content.replace(var_anchor, line + var_anchor, 1)
                modified = True
    else:
        # Insert after anchor (forward order)
        for _, _, var_name, default in SETTINGS_PROPS:
            if var_name not in content:
                line = f"\n  var {var_name}: Boolean by booleanValue({VAR_TO_CONST[var_name]}, {default})"
                content = content.replace(var_anchor, var_anchor + line, 1)
                modified = True

    if modified:
        path.write_text(content, encoding="utf-8")
        print("SettingsValues.kt: injected retention properties.")
    else:
        print("SettingsValues.kt: no changes needed.")


def inject_state():
    path = Path(STATE_FILE)
    if not path.exists():
        print(f"::warning:: {STATE_FILE} not found. Skipping.")
        return

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    content = "".join(lines)
    if "keepExpiringMessages" in content:
        print("ChatsSettingsState.kt: retention fields already present. Skipping.")
        return

    in_state = False
    inserted = False
    for i, line in enumerate(lines):
        if "data class ChatsSettingsState" in line:
            in_state = True
            continue
        if in_state and not inserted:
            if line.lstrip().startswith(")"):
                for field in STATE_FIELDS:
                    lines.insert(i, field)
                    i += 1
                inserted = True
                break

    if not inserted:
        print("::error:: Could not find closing ')' of ChatsSettingsState data class")
        sys.exit(1)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("ChatsSettingsState.kt: retention fields inserted.")


if __name__ == "__main__":
    try:
        inject_settings()
        inject_state()
    except Exception as e:
        print(f"::error:: Overlay script failed: {e}")
        sys.exit(1)
