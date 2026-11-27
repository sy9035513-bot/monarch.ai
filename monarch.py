"""
MONARCH - a personal voice assistant
- Responds when you say "Monarch ..."
- Stores ALL your data in ONE file: ~/monarch/monarch.db (SQLite)
- Optional: answers general questions using Claude (set ANTHROPIC_API_KEY)

Install:
    pip install SpeechRecognition pyttsx3 pyaudio anthropic

Run:
    python monarch.py
"""

import datetime
import os
import sqlite3

import pyttsx3
import speech_recognition as sr

WAKE_WORD = "monarch"
DB_PATH = os.path.join(os.path.expanduser("~"), "monarch", "monarch.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ---------- single place for all data ----------
db = sqlite3.connect(DB_PATH)
db.execute(
    "CREATE TABLE IF NOT EXISTS memory ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, text TEXT, created TEXT)"
)
db.commit()


def save(kind, text):
    db.execute(
        "INSERT INTO memory (kind, text, created) VALUES (?, ?, ?)",
        (kind, text, datetime.datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()


def search(term=None, limit=5):
    if term:
        rows = db.execute(
            "SELECT text FROM memory WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{term}%", limit),
        )
    else:
        rows = db.execute("SELECT text FROM memory ORDER BY id DESC LIMIT ?", (limit,))
    return [r[0] for r in rows]


# ---------- voice in / out ----------
engine = pyttsx3.init()
recognizer = sr.Recognizer()


def speak(text):
    print("Monarch:", text)
    engine.say(text)
    engine.runAndWait()


def listen():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, phrase_time_limit=8)
    try:
        return recognizer.recognize_google(audio).lower()  # needs internet
    except (sr.UnknownValueError, sr.RequestError):
        return ""


# ---------- optional AI brain ----------
def ask_ai(question):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return "I can't answer that yet. Set your Anthropic API key to enable general questions."
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    notes = "\n".join(search(limit=10))
    reply = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=300,
        system=(
            "You are Monarch, a personal voice assistant. Keep answers short and "
            "spoken-friendly. Known notes about the user:\n" + notes
        ),
        messages=[{"role": "user", "content": question}],
    )
    return reply.content[0].text


# ---------- command handling ----------
def handle(cmd):
    if cmd.startswith("remember"):
        text = cmd.replace("remember", "", 1).strip()
        save("note", text)
        speak("Okay, I will remember that.")
    elif "what do you remember" in cmd or cmd.startswith("recall"):
        term = cmd.replace("recall", "").replace("what do you remember", "").strip()
        items = search(term or None)
        speak("; ".join(items) if items else "I don't have anything saved yet.")
    elif "time" in cmd:
        speak(datetime.datetime.now().strftime("It is %I:%M %p."))
    elif "date" in cmd or "today" in cmd:
        speak(datetime.datetime.now().strftime("Today is %A, %d %B %Y."))
    elif cmd in ("exit", "quit", "goodbye", "stop"):
        speak("Goodbye.")
        raise SystemExit
    else:
        speak(ask_ai(cmd))


def main():
    speak("Monarch is online. Say my name to give a command.")
    while True:
        heard = listen()
        if not heard or WAKE_WORD not in heard:
            continue
        cmd = heard.split(WAKE_WORD, 1)[1].strip()
        if not cmd:
            speak("Yes?")
            cmd = listen()
        if cmd:
            handle(cmd)


if __name__ == "__main__":
    main()
