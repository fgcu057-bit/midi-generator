# MIDI Generator & Reader

A deterministic tool for translating between human-readable `.pattern` files and Standard MIDI Files (`.mid`). This tool is designed for a simple copy/paste workflow with ChatGPT.

## MIDI CREATOR

Use exactly this workflow to create or modify MIDI arrangements.

### Step 1 — Open the project
```bash
cd /Users/karenina/midi-generator
```

### Step 2 — Open the creator template
```bash
nano midi_creator_template.txt
```
1. Copy the entire contents of this file.
2. Paste them into ChatGPT.
3. Give ChatGPT the instructions for the MIDI you want created or changed.
4. ChatGPT will return the **COMPLETE replacement `.pattern`**.

### Step 3 — Create the new arrangement
```bash
nano arrangements/my_song.pattern
```
1. Paste the complete `.pattern` returned by ChatGPT.
2. Save and exit:
   - `Control + O`
   - `Enter`
   - `Control + X`

*Note: You can replace `my_song.pattern` with any filename you like.*

### Step 4 — Generate the MIDI
```bash
./.venv/bin/python generate.py arrangements/my_song.pattern
```
The MIDI file will be placed in the `output/` folder. 

**IMPORTANT**: The filename used in Step 3 must be the same filename used in Step 4.

---

## MIDI READER

Use exactly this workflow to extract musical information from a MIDI file for ChatGPT.

### Step 1 — Save MIDI from Logic
Save/export the MIDI from Logic Pro to your Desktop.

### Step 2 — Copy the MIDI's full path
Get the full filesystem path, for example:
`/Users/karenina/Desktop/my_song.mid`

### Step 3 — Open the project
```bash
cd /Users/karenina/midi-generator
```

### Step 4 — Open the reader template
```bash
nano midi_reader_template.py
```
1. Find the line `MIDI_PATH = "..."` and change it to your MIDI's full path.
2. Save this as a **NEW** reader script rather than overwriting the template.
   - `Control + O`
   - Type a new name (e.g., `midi_my_song.py`)
   - `Enter`
   - `Control + X`

**Do not overwrite `midi_reader_template.py`.**

### Step 5 — Run the new reader
```bash
./.venv/bin/python midi_my_song.py
```

### Step 6 — Copy the results
Copy the entire Terminal output and paste it into ChatGPT. This output provides the musical information ChatGPT needs to understand your arrangement.

---

## QUICK REFERENCE

**CREATE:**
```text
cd /Users/karenina/midi-generator
nano midi_creator_template.txt
COPY → CHATGPT
nano arrangements/my_song.pattern
PASTE → SAVE
./.venv/bin/python generate.py arrangements/my_song.pattern
```

**READ:**
```text
Save MIDI from Logic
Copy MIDI path

cd /Users/karenina/midi-generator
nano midi_reader_template.py
CHANGE MIDI_PATH
SAVE AS NEW FILE (e.g. midi_my_song.py)
./.venv/bin/python midi_my_song.py
COPY TERMINAL → CHATGPT
```
