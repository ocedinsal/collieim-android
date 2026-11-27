"""Insert retention fields into ChatsSettingsState.kt data class."""
import sys

FILE = "feature/app-settings/src/main/java/org/signal/appsettings/chats/ChatsSettingsState.kt"

FIELDS = [
    "  ,\n",
    "  val keepExpiringMessages: Boolean = false,\n",
    "  val keepViewOnceMessages: Boolean = false,\n",
    "  val ignoreRemoteDelete: Boolean = false,\n",
    "  val deleteMediaOnly: Boolean = false\n",
]

def main():
    with open(FILE, "r") as f:
        lines = f.readlines()

    # Idempotency: skip if already present
    content = "".join(lines)
    if "keepExpiringMessages" in content:
        print("Retention fields already present. Skipping.")
        return

    # Find the closing ')' of the data class parameter list
    in_state = False
    inserted = False
    for i, line in enumerate(lines):
        if "data class ChatsSettingsState" in line:
            in_state = True
            continue
        if in_state and not inserted:
            stripped = line.lstrip()
            if stripped.startswith(")"):
                for field in FIELDS:
                    lines.insert(i, field)
                    i += 1
                inserted = True
                break

    if not inserted:
        print("::error::Could not find closing ')' of ChatsSettingsState data class")
        sys.exit(1)

    with open(FILE, "w") as f:
        f.writelines(lines)
    print("Retention fields inserted into ChatsSettingsState.kt")

if __name__ == "__main__":
    main()
