# UPA Arts ONE — Personalisation Script
## How it works

The script patches your GIMP `.xcf` templates — replacing the student name text layer automatically — then exports a ready-to-print PNG for each student. No GIMP interface needed.

---

## Setup (one time only)

1. Copy these files into your UPA Dropbox folder:
   ```
   /Users/soul2sole/Dropbox/DTF Files/UPA/
   ├── upa_personalise.py
   └── UPA Personalise.command
   ```

2. Make the launcher executable. Open Terminal and run:
   ```
   chmod +x "/Users/soul2sole/Dropbox/DTF Files/UPA/UPA Personalise.command"
   ```

3. Install the PDF reading library (if you want PDF support):
   ```
   pip3 install pypdf
   ```

4. Make sure your XCF templates are in your logos folder:
   ```
   /Users/soul2sole/Dropbox/DTF Files/UPA/logos/gimp files/
   ├── adult__FOR__personlalization_245mm____90mm_combined_logo_.xcf
   ├── childs_FOR_personalization_190mm____85mm_combined_logo_.xcf
   └── xl_adult__FOR__personlalization_275mm___100_mm_combined_logo_.xcf
   ```

---

## Day-to-day use

### Option 1 — Double-click (interactive)
Double-click **UPA Personalise.command**. You'll be asked:
- Which size (child / adult / xl)
- The student names (comma-separated)

It then generates all the PNGs into a new timestamped folder inside `print today`.

### Option 2 — From Terminal (faster for batches)

**Type names directly:**
```bash
python3 upa_personalise.py --names "Alice Smith, Bob Jones, Clara Wu" --size adult
```

**From a text file (one name per line, with size):**
```bash
python3 upa_personalise.py --list order_names.txt
```

Format of the text file:
```
Alice Smith, adult
Bob Jones, child
Clara Wu, xl
```

**From the order PDF:**
```bash
python3 upa_personalise.py --pdf "/path/to/order.pdf"
```
> ⚠ PDF extraction depends on the layout of your order form. If it doesn't pick up names correctly, use the text file or interactive mode instead, and let us know the form layout so we can tune it.

---

## Output

Files are saved to:
```
/Users/soul2sole/Dropbox/DTF Files/print today/ArtsONE_personalised_2026-05-23_1430/
├── ArtsONE_Alice_Smith_adult.png
├── ArtsONE_Bob_Jones_child.png
└── ArtsONE_Clara_Wu_xl_adult.png
```

Import this folder into your print software as normal.

---

## Adding a new Arts ONE size/variant

If Arts ONE adds a new garment size with a different XCF template:
1. Add the XCF file to your logos/gimp files folder
2. Open `upa_personalise.py` and add a line to the `TEMPLATES` dict:
   ```python
   TEMPLATES = {
       "child":    "childs_FOR_..._combined_logo_.xcf",
       "adult":    "adult__FOR_..._combined_logo_.xcf",
       "xl_adult": "xl_adult__FOR_..._combined_logo_.xcf",
       "xxl":      "xxl_adult__FOR_..._combined_logo_.xcf",  ← add here
   }
   ```

---

## If something goes wrong

**"Could not find name markup"**  
→ The XCF template may have a different text layer format. Send the new XCF to Claude for an update.

**"GIMP not found"**  
→ The script saves XCF files instead of PNGs. Open them manually in GIMP and export, or install GIMP from gimp.org.

**"template not found"**  
→ Check the XCF filenames in the logos folder match exactly what's in the `TEMPLATES` dict in the script.

---

*Built with Claude — May 2026*
