#!/bin/bash
# UPA Arts ONE — Personalisation Launcher
# Double-click this file to run the personalisation script.
#
# USAGE:
#   1. In the web app, go to the Personalisation tab
#   2. Enter student name(s) and size — click Copy on the terminal command
#   3. Double-click this file — it reads from your clipboard and runs
#
# If it won't open, run this in Terminal:
#   chmod +x "/Users/soul2sole/Dropbox/DTF Files/UPA/UPA Personalise.command"
#   xattr -d com.apple.quarantine "/Users/soul2sole/Dropbox/DTF Files/UPA/UPA Personalise.command"

cd "/Users/soul2sole/Dropbox/DTF Files/UPA"

# Read clipboard
CLIPBOARD=$(pbpaste)

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  UPA Arts ONE — Personalisation Launcher"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check clipboard contains a valid personalise command
if echo "$CLIPBOARD" | grep -q "upa_personalise.py"; then
    echo "  Running command from clipboard:"
    echo "  $CLIPBOARD"
    echo ""
    eval "$CLIPBOARD"
else
    echo "  Nothing found on clipboard."
    echo ""
    echo "  To use this launcher:"
    echo "    1. Open the web app and go to the Personalisation tab"
    echo "    2. Enter student name(s) and click Copy on the terminal command"
    echo "    3. Double-click this file again"
    echo ""
    echo "  Or run manually — example:"
    echo "    python3 upa_personalise.py --names \"Ariana\" --size child"
    echo ""
fi

echo ""
echo "Press any key to close..."
read -n 1
