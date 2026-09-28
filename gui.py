import json
import os
import re
import threading
import tkinter as tk
from tkinter import ttk

from ai_services import AIProvider


# ============================================================
# CONFIG
# ============================================================

APP_TITLE = "Jarvis"
MEMORY_FILE = "memory.json"

BG_COLOR = "#000000"
CHAT_COLOR = "#000000"
SIDEBAR_COLOR = "#080808"
INPUT_COLOR = "#111111"
BUTTON_COLOR = "#151515"
BUTTON_HOVER = "#222222"
BUTTON_DISABLED = "#303030"

TEXT_COLOR = "#FFFFFF"
SECONDARY_TEXT = "#888888"
MUTED_TEXT = "#5F5F5F"

BORDER_COLOR = "#222222"
ACCENT_COLOR = "#FFFFFF"

DANGER_COLOR = "#E53935"
DANGER_HOVER = "#FF4D4D"
DANGER_BG = "#241010"

SIDEBAR_WIDTH = 235

MAX_MEMORY_FACTS = 100
MAX_PENDING_FACTS = 10
MAX_RECENT_CHATS = 30

SETTINGS_WIDTH = 620
SETTINGS_HEIGHT = 500

ANIMATION_STEPS = 10
ANIMATION_DELAY = 15


# ============================================================
# GLOBAL STATE
# ============================================================

ai = AIProvider()

memory = {}
pending_private_facts = []

is_processing = False

sidebar_visible = True

active_chat_id = None

# In-app panels
settings_panel = None
settings_overlay = None

delete_overlay = None
delete_card = None

# Inline rename
rename_entry = None
rename_chat_id = None

# Prevent duplicate operations
panel_animating = False

menu_buttons = {}


# ============================================================
# PRIVACY
# ============================================================

BLOCKED_PATTERNS = [
    r"\bpassword\b",
    r"\bpasscode\b",
    r"\bapi[\s_-]?key\b",
    r"\bsecret[\s_-]?key\b",
    r"\bprivate[\s_-]?key\b",
    r"\baccess[\s_-]?token\b",
    r"\bauth[\s_-]?token\b",
    r"\bbearer[\s_-]?token\b",
    r"\bclient[\s_-]?secret\b",
    r"\bverification[\s_-]?code\b",
    r"\bsecurity[\s_-]?code\b",
    r"\bone[\s_-]?time[\s_-]?password\b",
    r"\botp\b",
    r"\bpin\b",
]

PRIVATE_PATTERNS = [
    r"\bmy address\b",
    r"\bmy location\b",
    r"\bwhere i live\b",
    r"\bmy phone\b",
    r"\bmy mobile\b",
    r"\bmy email\b",
    r"\bmy birthday\b",
    r"\bmy school\b",
    r"\bmy workplace\b",
    r"\bmy company\b",
    r"\bmy parents\b",
    r"\bmy family\b",
    r"\bmy brother\b",
    r"\bmy sister\b",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def contains_blocked_information(text):
    text = text.lower()

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def contains_private_information(text):
    text = text.lower()

    for pattern in PRIVATE_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def generate_id():
    import uuid
    return str(uuid.uuid4())


def now_chat():
    return {
        "id": generate_id(),
        "title": "New Chat",
        "messages": []
    }


def default_memory():
    return {
        "conversation": [],
        "facts": [],
        "chats": []
    }


# ============================================================
# MEMORY
# ============================================================

def load_memory():
    global memory
    global active_chat_id

    if not os.path.exists(MEMORY_FILE):
        memory = default_memory()
        chat = now_chat()
        memory["chats"].append(chat)
        active_chat_id = chat["id"]
        return

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = default_memory()

        memory = data

    except Exception:
        memory = default_memory()

    if not isinstance(memory.get("facts"), list):
        memory["facts"] = []

    if not isinstance(memory.get("chats"), list):
        memory["chats"] = []

    # --------------------------------------------------------
    # Sanitize facts
    # --------------------------------------------------------

    clean_facts = []

    for fact in memory["facts"]:
        if isinstance(fact, str) and fact.strip():
            if not contains_blocked_information(fact):
                clean_facts.append(fact.strip())

    memory["facts"] = clean_facts[:MAX_MEMORY_FACTS]

    # --------------------------------------------------------
    # Sanitize chats
    # --------------------------------------------------------

    clean_chats = []

    for chat in memory["chats"]:

        if not isinstance(chat, dict):
            continue

        chat_id = chat.get("id") or generate_id()

        title = chat.get("title", "New Chat")

        if not isinstance(title, str) or not title.strip():
            title = "New Chat"

        messages = chat.get("messages", [])

        if not isinstance(messages, list):
            messages = []

        clean_messages = []

        for message in messages:

            if not isinstance(message, dict):
                continue

            role = message.get("role")
            content = message.get("content")

            if role not in ("user", "assistant", "system"):
                continue

            if not isinstance(content, str):
                continue

            clean_messages.append({
                "role": role,
                "content": content
            })

        clean_chat = {
            "id": chat_id,
            "title": title,
            "messages": clean_messages
        }

        clean_chats.append(clean_chat)

    memory["chats"] = clean_chats

    # --------------------------------------------------------
    # Migrate old conversation format
    # --------------------------------------------------------

    if not memory["chats"]:

        old_conversation = memory.get("conversation", [])

        if isinstance(old_conversation, list) and old_conversation:

            migrated = now_chat()
            migrated["messages"] = old_conversation

            first_user = get_first_user_message(migrated)

            if first_user:
                migrated["title"] = fallback_chat_title(first_user)

            memory["chats"].append(migrated)

    # --------------------------------------------------------
    # Always have one empty working chat
    # --------------------------------------------------------

    if not memory["chats"]:
        memory["chats"].append(now_chat())

    # --------------------------------------------------------
    # Fix old "New Chat" titles
    # --------------------------------------------------------

    ensure_chat_titles()

    # --------------------------------------------------------
    # Active chat
    # --------------------------------------------------------

    active_chat_id = memory["chats"][-1]["id"]


def save_memory():
    try:

        active = get_active_chat()

        if active:
            memory["conversation"] = active.get("messages", [])

        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                memory,
                f,
                indent=2,
                ensure_ascii=False
            )

    except Exception as e:
        print("Memory save error:", e)


def ensure_chat_titles():
    """
    Fix old conversations that still have 'New Chat'
    even though they contain real messages.
    """

    for chat in memory.get("chats", []):

        if not chat.get("messages"):
            continue

        if chat.get("title") != "New Chat":
            continue

        first_user = get_first_user_message(chat)

        if first_user:
            if contains_blocked_information(first_user):
                chat["title"] = "Private Interaction"
            else:
                chat["title"] = fallback_chat_title(first_user)


def get_first_user_message(chat):
    for message in chat.get("messages", []):
        if message.get("role") == "user":
            return message.get("content", "").strip()

    return ""


def get_active_chat():

    global active_chat_id

    for chat in memory.get("chats", []):

        if chat.get("id") == active_chat_id:
            return chat

    if memory.get("chats"):
        active_chat_id = memory["chats"][-1]["id"]
        return memory["chats"][-1]

    chat = now_chat()

    memory["chats"].append(chat)

    active_chat_id = chat["id"]

    return chat


# ============================================================
# CHAT TITLES
# ============================================================

def fallback_chat_title(message):

    message = re.sub(r"\s+", " ", message.strip())

    if not message:
        return "Untitled Chat"

    message = re.sub(r"^[/#]+", "", message).strip()

    words = message.split()

    if len(words) > 7:
        title = " ".join(words[:7]) + "..."
    else:
        title = " ".join(words)

    title = title[:70].strip()

    return title or "Untitled Chat"


def generate_chat_title(user_message):

    if contains_blocked_information(user_message):
        return "Private Interaction"

    prompt = f"""
Create a short title for this conversation.

Rules:
- 2 to 6 words
- Do not use quotation marks
- Do not use emojis
- Do not include personal information
- Describe the main topic
- Return only the title

User's first message:
{user_message}
"""

    try:

        result = ai.chat(
            [
                {
                    "role": "system",
                    "content": "You create concise conversation titles."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        title = result.strip()

        title = title.replace('"', "")
        title = title.replace("'", "")
        title = re.sub(r"\s+", " ", title)

        if not title:
            raise ValueError("Empty title")

        if len(title) > 70:
            raise ValueError("Title too long")

        if contains_blocked_information(title):
            raise ValueError("Private information in title")

        return title

    except Exception:
        return fallback_chat_title(user_message)


# ============================================================
# AI MESSAGES
# ============================================================

def build_messages(chat):

    messages = []

    system_prompt = """
You are Jarvis, a helpful local AI assistant.

Be concise, useful, and conversational.

Respect user privacy.
Never ask the user to reveal passwords, API keys,
authentication tokens, private keys, verification codes,
or other sensitive secrets.

If the user provides sensitive information accidentally,
do not save or repeat it unnecessarily.
"""

    messages.append({
        "role": "system",
        "content": system_prompt
    })

    for fact in memory.get("facts", []):

        if contains_blocked_information(fact):
            continue

        messages.append({
            "role": "system",
            "content": f"Known user preference/fact: {fact}"
        })

    for message in chat.get("messages", []):

        if message.get("role") in ("user", "assistant"):

            messages.append({
                "role": message["role"],
                "content": message["content"]
            })

    return messages


# ============================================================
# MEMORY EXTRACTION
# ============================================================

def extract_facts(chat, user_message):

    if contains_blocked_information(user_message):
        return []

    prompt = f"""
Look at the user's message and identify stable,
non-sensitive facts or preferences that could be useful
in future conversations.

Return ONLY a JSON array of strings.

Do not save:
- passwords
- API keys
- tokens
- private keys
- verification codes
- PINs
- addresses
- phone numbers
- emails
- precise locations
- sensitive personal information

If there is nothing useful, return [].

User message:
{user_message}
"""

    try:

        result = ai.chat(
            [
                {
                    "role": "system",
                    "content": "You extract safe long-term user preferences."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1
        )

        match = re.search(r"\[[\s\S]*\]", result)

        if not match:
            return []

        facts = json.loads(match.group(0))

        if not isinstance(facts, list):
            return []

        safe = []

        for fact in facts:

            if not isinstance(fact, str):
                continue

            fact = fact.strip()

            if not fact:
                continue

            if contains_blocked_information(fact):
                continue

            if contains_private_information(fact):
                continue

            safe.append(fact)

        return safe[:MAX_PENDING_FACTS]

    except Exception:
        return []


def add_safe_memory(facts):

    changed = False

    for fact in facts:

        if not isinstance(fact, str):
            continue

        fact = fact.strip()

        if not fact:
            continue

        if contains_blocked_information(fact):
            continue

        if contains_private_information(fact):
            continue

        if fact not in memory["facts"]:

            memory["facts"].append(fact)

            changed = True

    memory["facts"] = memory["facts"][-MAX_MEMORY_FACTS:]

    return changed


# ============================================================
# UI HELPERS
# ============================================================

def set_status(text):

    if "status_label" in globals() and status_label.winfo_exists():
        status_label.config(text=text)


def add_hover(widget, normal, hover):

    def enter(_):
        if widget.cget("state") != "disabled":
            widget.configure(bg=hover)

    def leave(_):
        if widget.cget("state") != "disabled":
            widget.configure(bg=normal)

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


def set_button_enabled(button, enabled):

    if enabled:
        button.configure(
            state="normal",
            bg=BUTTON_COLOR
        )
    else:
        button.configure(
            state="disabled",
            bg=BUTTON_DISABLED
        )


def set_processing(processing):

    global is_processing

    is_processing = processing

    if processing:

        send_button.configure(
            state="disabled",
            bg=BUTTON_DISABLED
        )

        set_status("Thinking...")

    else:

        send_button.configure(
            state="normal",
            bg=BUTTON_COLOR
        )

        set_status("Ready")


# ============================================================
# MESSAGE DISPLAY
# ============================================================

def display_message(role, content):

    if role == "user":

        wrapper = tk.Frame(
            messages_frame,
            bg=CHAT_COLOR
        )

        wrapper.pack(
            fill="x",
            padx=24,
            pady=(10, 4)
        )

        bubble = tk.Frame(
            wrapper,
            bg="#202020"
        )

        bubble.pack(
            side="right",
            padx=(100, 0)
        )

        label = tk.Label(
            bubble,
            text=content,
            bg="#202020",
            fg=TEXT_COLOR,
            font=("Segoe UI", 10),
            justify="left",
            anchor="w",
            wraplength=620,
            padx=14,
            pady=10
        )

        label.pack()

    else:

        wrapper = tk.Frame(
            messages_frame,
            bg=CHAT_COLOR
        )

        wrapper.pack(
            fill="x",
            padx=24,
            pady=(4, 10)
        )

        bubble = tk.Frame(
            wrapper,
            bg="#111111"
        )

        bubble.pack(
            side="left",
            padx=(0, 100)
        )

        label = tk.Label(
            bubble,
            text=content,
            bg="#111111",
            fg=TEXT_COLOR,
            font=("Segoe UI", 10),
            justify="left",
            anchor="w",
            wraplength=700,
            padx=14,
            pady=10
        )

        label.pack()

    root.after(
        20,
        lambda: chat_canvas.yview_moveto(1.0)
    )


def clear_display():

    for widget in messages_frame.winfo_children():
        widget.destroy()


def display_current_chat():

    clear_display()

    chat = get_active_chat()

    for message in chat.get("messages", []):

        display_message(
            message.get("role"),
            message.get("content", "")
        )

    update_chat_header()


def update_chat_header():

    chat = get_active_chat()

    title = chat.get("title", "New Chat")

    if title == "New Chat" and chat.get("messages"):

        first = get_first_user_message(chat)

        if first:
            title = fallback_chat_title(first)

            chat["title"] = title

    chat_title_label.configure(
        text=title
    )


# ============================================================
# RECENT INTERACTIONS
# ============================================================

def update_history():

    global menu_buttons

    for widget in history_frame.winfo_children():
        widget.destroy()

    menu_buttons = {}

    chats = [
        chat
        for chat in memory.get("chats", [])
        if chat.get("messages")
    ]

    chats = list(reversed(chats))

    if not chats:

        empty_label = tk.Label(
            history_frame,
            text="No recent interactions",
            bg=SIDEBAR_COLOR,
            fg=MUTED_TEXT,
            font=("Segoe UI", 9)
        )

        empty_label.pack(
            anchor="w",
            padx=12,
            pady=12
        )

        return

    for chat in chats[:MAX_RECENT_CHATS]:

        create_history_item(chat)


def create_history_item(chat):

    chat_id = chat["id"]

    selected = chat_id == active_chat_id

    row_bg = "#181818" if selected else SIDEBAR_COLOR

    row = tk.Frame(
        history_frame,
        bg=row_bg,
        height=42
    )

    row.pack(
        fill="x",
        padx=8,
        pady=2
    )

    row.pack_propagate(False)

    title = chat.get("title", "Untitled Chat")

    title_button = tk.Button(
        row,
        text=title,
        bg=row_bg,
        fg=TEXT_COLOR if selected else "#BDBDBD",
        activebackground="#222222",
        activeforeground=TEXT_COLOR,
        font=("Segoe UI", 9),
        bd=0,
        relief="flat",
        anchor="w",
        padx=8,
        cursor="hand2",
        command=lambda cid=chat_id: select_chat(cid)
    )

    title_button.pack(
        side="left",
        fill="both",
        expand=True
    )

    menu_button = tk.Button(
        row,
        text="⋮",
        bg=row_bg,
        fg=SECONDARY_TEXT,
        activebackground="#222222",
        activeforeground=TEXT_COLOR,
        font=("Segoe UI", 13),
        bd=0,
        relief="flat",
        width=3,
        cursor="hand2",
        command=lambda cid=chat_id: show_chat_menu(cid)
    )

    menu_button.pack(
        side="right",
        fill="y"
    )

    add_hover(
        title_button,
        row_bg,
        "#202020"
    )

    add_hover(
        menu_button,
        row_bg,
        "#202020"
    )

    menu_buttons[chat_id] = menu_button


def select_chat(chat_id):

    global active_chat_id

    if rename_entry is not None:
        finish_inline_rename(cancel=True)

    close_delete_overlay()

    active_chat_id = chat_id

    display_current_chat()
    update_history()
    save_memory()


# ============================================================
# NEW CHAT
# ============================================================

def new_chat():

    global active_chat_id

    if is_processing:
        return

    if rename_entry is not None:
        finish_inline_rename(cancel=True)

    close_delete_overlay()

    chat = now_chat()

    memory["chats"].append(chat)

    active_chat_id = chat["id"]

    clear_display()

    update_chat_header()
    update_history()

    input_box.focus_set()


# ============================================================
# INLINE RENAME
# ============================================================

def start_inline_rename(chat_id):

    global rename_entry
    global rename_chat_id

    if is_processing:
        return

    if rename_entry is not None:
        finish_inline_rename(cancel=True)

    chat = None

    for item in memory["chats"]:
        if item["id"] == chat_id:
            chat = item
            break

    if chat is None:
        return

    # Rebuild history item in-place by locating the row
    for row in history_frame.winfo_children():

        children = row.winfo_children()

        if not children:
            continue

        title_button = children[0]

        if not isinstance(title_button, tk.Button):
            continue

        current_title = chat.get("title", "New Chat")

        if title_button.cget("text") != current_title:
            continue

        title_button.pack_forget()

        rename_entry = tk.Entry(
            row,
            bg="#161616",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            selectbackground="#444444",
            selectforeground=TEXT_COLOR,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9)
        )

        rename_entry.insert(
            0,
            current_title
        )

        rename_entry.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(7, 2),
            pady=7
        )

        rename_chat_id = chat_id

        rename_entry.focus_set()
        rename_entry.select_range(0, tk.END)

        rename_entry.bind(
            "<Return>",
            lambda event: (
                finish_inline_rename(),
                "break"
            )
        )

        rename_entry.bind(
            "<Escape>",
            lambda event: (
                finish_inline_rename(cancel=True),
                "break"
            )
        )

        return


def finish_inline_rename(cancel=False):

    global rename_entry
    global rename_chat_id

    if rename_entry is None:
        return

    chat_id = rename_chat_id

    if not cancel:

        new_title = rename_entry.get().strip()

        if new_title:

            new_title = re.sub(
                r"\s+",
                " ",
                new_title
            )

            new_title = new_title[:70]

            for chat in memory["chats"]:

                if chat["id"] == chat_id:
                    chat["title"] = new_title
                    break

    rename_entry.destroy()

    rename_entry = None
    rename_chat_id = None

    update_history()
    update_chat_header()

    save_memory()


# ============================================================
# CHAT MENU
# ============================================================

def show_chat_menu(chat_id):

    # Close existing menu first
    close_chat_menu()

    button = menu_buttons.get(chat_id)

    if button is None:
        return

    menu = tk.Frame(
        root,
        bg="#171717",
        highlightbackground="#303030",
        highlightthickness=1
    )

    menu.place(
        x=SIDEBAR_WIDTH - 170,
        y=button.winfo_rooty() - root.winfo_rooty() + 25,
        width=150
    )

    rename_button = tk.Button(
        menu,
        text="Rename",
        bg="#171717",
        fg=TEXT_COLOR,
        activebackground="#252525",
        activeforeground=TEXT_COLOR,
        font=("Segoe UI", 9),
        bd=0,
        relief="flat",
        anchor="w",
        padx=12,
        command=lambda: (
            menu.destroy(),
            start_inline_rename(chat_id)
        )
    )

    rename_button.pack(
        fill="x",
        ipady=7
    )

    delete_button = tk.Button(
        menu,
        text="Delete",
        bg="#171717",
        fg="#FF7777",
        activebackground="#351414",
        activeforeground="#FF7777",
        font=("Segoe UI", 9),
        bd=0,
        relief="flat",
        anchor="w",
        padx=12,
        command=lambda: (
            menu.destroy(),
            show_delete_confirmation(chat_id)
        )
    )

    delete_button.pack(
        fill="x",
        ipady=7
    )

    root._chat_menu = menu


def close_chat_menu():

    menu = getattr(root, "_chat_menu", None)

    if menu is not None:

        try:
            menu.destroy()
        except Exception:
            pass

        root._chat_menu = None


# ============================================================
# DELETE CONFIRMATION
# ============================================================

def show_delete_confirmation(chat_id):

    global delete_overlay
    global delete_card

    close_chat_menu()

    if delete_overlay is not None:
        return

    chat = None

    for item in memory["chats"]:

        if item["id"] == chat_id:
            chat = item
            break

    if chat is None:
        return

    delete_overlay = tk.Frame(
        main_area,
        bg="#000000"
    )

    delete_overlay.place(
        relx=0,
        rely=0,
        relwidth=1,
        relheight=1
    )

    delete_card = tk.Frame(
        delete_overlay,
        bg="#111111",
        highlightbackground="#303030",
        highlightthickness=1
    )

    delete_card.place(
        relx=0.5,
        rely=0.5,
        anchor="center",
        relwidth=0.55,
        relheight=0.35
    )

    title = tk.Label(
        delete_card,
        text="Delete this interaction?",
        bg="#111111",
        fg=TEXT_COLOR,
        font=("Segoe UI", 15, "bold")
    )

    title.pack(
        pady=(28, 12)
    )

    subtitle = tk.Label(
        delete_card,
        text="This action cannot be undone.",
        bg="#111111",
        fg=SECONDARY_TEXT,
        font=("Segoe UI", 9)
    )

    subtitle.pack(
        pady=(0, 18)
    )

    # Red highlighted chat title
    title_box = tk.Frame(
        delete_card,
        bg=DANGER_BG,
        highlightbackground="#662020",
        highlightthickness=1
    )

    title_box.pack(
        fill="x",
        padx=35,
        pady=(0, 25)
    )

    chat_title = tk.Label(
        title_box,
        text=chat.get("title", "Untitled Chat"),
        bg=DANGER_BG,
        fg="#FF6666",
        font=("Segoe UI", 10, "bold"),
        wraplength=380
    )

    chat_title.pack(
        padx=14,
        pady=12
    )

    buttons = tk.Frame(
        delete_card,
        bg="#111111"
    )

    buttons.pack(
        side="bottom",
        pady=20
    )

    cancel = tk.Button(
        buttons,
        text="Cancel",
        bg="#1A1A1A",
        fg=TEXT_COLOR,
        activebackground="#292929",
        activeforeground=TEXT_COLOR,
        font=("Segoe UI", 9),
        bd=0,
        relief="flat",
        padx=24,
        pady=9,
        cursor="hand2",
        command=close_delete_overlay
    )

    cancel.pack(
        side="left",
        padx=6
    )

    delete = tk.Button(
        buttons,
        text="Delete",
        bg=DANGER_COLOR,
        fg="white",
        activebackground=DANGER_HOVER,
        activeforeground="white",
        font=("Segoe UI", 9, "bold"),
        bd=0,
        relief="flat",
        padx=24,
        pady=9,
        cursor="hand2",
        command=lambda: delete_chat(chat_id)
    )

    delete.pack(
        side="left",
        padx=6
    )

    add_hover(
        cancel,
        "#1A1A1A",
        "#292929"
    )

    add_hover(
        delete,
        DANGER_COLOR,
        DANGER_HOVER
    )

    # Fade-like reveal
    animate_delete_card()


def animate_delete_card():

    if delete_card is None:
        return

    # Small slide upward effect
    try:
        delete_card.place_configure(
            rely=0.48
        )

        root.after(
            30,
            lambda: delete_card.place_configure(
                rely=0.49
            )
        )

        root.after(
            60,
            lambda: delete_card.place_configure(
                rely=0.5
            )
        )

    except tk.TclError:
        pass


def close_delete_overlay():

    global delete_overlay
    global delete_card

    if delete_overlay is None:
        return

    try:
        delete_overlay.destroy()
    except Exception:
        pass

    delete_overlay = None
    delete_card = None


def delete_chat(chat_id):

    global active_chat_id

    if is_processing:
        return

    target_index = None

    for index, chat in enumerate(memory["chats"]):

        if chat["id"] == chat_id:
            target_index = index
            break

    if target_index is None:
        close_delete_overlay()
        return

    del memory["chats"][target_index]

    # Always keep one empty working chat
    if not memory["chats"]:

        chat = now_chat()

        memory["chats"].append(chat)

        active_chat_id = chat["id"]

    elif active_chat_id == chat_id:

        # Select newest remaining chat
        active_chat_id = memory["chats"][-1]["id"]

    close_delete_overlay()

    display_current_chat()
    update_history()
    save_memory()


# ============================================================
# CLEAR CURRENT CHAT
# ============================================================

def clear_current_chat():

    if is_processing:
        return

    chat = get_active_chat()

    chat["messages"] = []
    chat["title"] = "New Chat"

    clear_display()

    update_chat_header()
    update_history()

    save_memory()


# ============================================================
# FORGET MEMORY
# ============================================================

def forget_memory():

    memory["facts"] = []

    save_memory()

    set_status("Memory cleared")

    root.after(
        1800,
        lambda: set_status("Ready")
    )


# ============================================================
# SIDEBAR
# ============================================================

def toggle_sidebar():

    global sidebar_visible

    if sidebar_visible:

        sidebar.grid_remove()

        sidebar_visible = False

    else:

        sidebar.grid()

        sidebar_visible = True


# ============================================================
# SETTINGS
# ============================================================

def open_settings():

    global settings_panel
    global settings_overlay

    if settings_panel is not None:

        close_settings()

        return

    close_chat_menu()
    close_delete_overlay()

    settings_overlay = tk.Frame(
        main_area,
        bg="#000000"
    )

    settings_overlay.place(
        relx=0,
        rely=0,
        relwidth=1,
        relheight=1
    )

    settings_panel = tk.Frame(
        settings_overlay,
        bg="#111111",
        highlightbackground="#303030",
        highlightthickness=1
    )

    settings_panel.place(
        relx=0.5,
        rely=0.47,
        anchor="center",
        relwidth=0.72,
        relheight=0.76
    )

    build_settings_panel(settings_panel)

    animate_settings_in()


def animate_settings_in():

    if settings_panel is None:
        return

    try:

        settings_panel.place_configure(
            rely=0.44
        )

        root.after(
            25,
            lambda: settings_panel.place_configure(
                rely=0.45
            )
        )

        root.after(
            50,
            lambda: settings_panel.place_configure(
                rely=0.46
            )
        )

        root.after(
            75,
            lambda: settings_panel.place_configure(
                rely=0.47
            )
        )

    except tk.TclError:
        pass


def close_settings():

    global settings_panel
    global settings_overlay

    if settings_panel is not None:

        try:
            settings_panel.destroy()
        except Exception:
            pass

    if settings_overlay is not None:

        try:
            settings_overlay.destroy()
        except Exception:
            pass

    settings_panel = None
    settings_overlay = None


def build_settings_panel(parent):

    header = tk.Frame(
        parent,
        bg="#111111"
    )

    header.pack(
        fill="x",
        padx=28,
        pady=(22, 10)
    )

    title = tk.Label(
        header,
        text="Settings",
        bg="#111111",
        fg=TEXT_COLOR,
        font=("Segoe UI", 16, "bold")
    )

    title.pack(
        side="left"
    )

    close = tk.Button(
        header,
        text="×",
        bg="#111111",
        fg=SECONDARY_TEXT,
        activebackground="#222222",
        activeforeground=TEXT_COLOR,
        font=("Segoe UI", 18),
        bd=0,
        relief="flat",
        cursor="hand2",
        command=close_settings
    )

    close.pack(
        side="right"
    )

    add_hover(
        close,
        "#111111",
        "#222222"
    )

    content = tk.Frame(
        parent,
        bg="#111111"
    )

    content.pack(
        fill="both",
        expand=True,
        padx=38,
        pady=10
    )

    # Provider
    tk.Label(
        content,
        text="Provider",
        bg="#111111",
        fg=SECONDARY_TEXT,
        font=("Segoe UI", 9)
    ).pack(
        anchor="w"
    )

    provider_var = tk.StringVar(
        value=getattr(ai, "provider", "ollama")
    )

    provider_box = ttk.Combobox(
        content,
        textvariable=provider_var,
        values=["ollama", "custom"],
        state="readonly",
        font=("Segoe UI", 9)
    )

    provider_box.pack(
        fill="x",
        pady=(5, 15)
    )

    # Model
    tk.Label(
        content,
        text="Model",
        bg="#111111",
        fg=SECONDARY_TEXT,
        font=("Segoe UI", 9)
    ).pack(
        anchor="w"
    )

    model_var = tk.StringVar(
        value=getattr(
            ai,
            "model",
            "qwen2.5-coder:7b"
        )
    )

    model_entry = tk.Entry(
        content,
        textvariable=model_var,
        bg="#181818",
        fg=TEXT_COLOR,
        insertbackground=TEXT_COLOR,
        relief="flat",
        bd=0,
        font=("Segoe UI", 10)
    )

    model_entry.pack(
        fill="x",
        ipady=8,
        pady=(5, 15)
    )

    # Base URL
    tk.Label(
        content,
        text="Base URL",
        bg="#111111",
        fg=SECONDARY_TEXT,
        font=("Segoe UI", 9)
    ).pack(
        anchor="w"
    )

    base_url_var = tk.StringVar(
        value=getattr(
            ai,
            "base_url",
            "http://localhost:11434/v1"
        )
    )

    base_url_entry = tk.Entry(
        content,
        textvariable=base_url_var,
        bg="#181818",
        fg=TEXT_COLOR,
        insertbackground=TEXT_COLOR,
        relief="flat",
        bd=0,
        font=("Segoe UI", 10)
    )

    base_url_entry.pack(
        fill="x",
        ipady=8,
        pady=(5, 15)
    )

    # API key
    tk.Label(
        content,
        text="API Key",
        bg="#111111",
        fg=SECONDARY_TEXT,
        font=("Segoe UI", 9)
    ).pack(
        anchor="w"
    )

    api_key_var = tk.StringVar(
        value=getattr(
            ai,
            "api_key",
            "ollama"
        )
    )

    api_key_entry = tk.Entry(
        content,
        textvariable=api_key_var,
        bg="#181818",
        fg=TEXT_COLOR,
        insertbackground=TEXT_COLOR,
        relief="flat",
        bd=0,
        font=("Segoe UI", 10),
        show="•"
    )

    api_key_entry.pack(
        fill="x",
        ipady=8,
        pady=(5, 20)
    )

    # Status
    settings_status = tk.Label(
        content,
        text="",
        bg="#111111",
        fg=SECONDARY_TEXT,
        font=("Segoe UI", 9)
    )

    settings_status.pack(
        anchor="w",
        pady=(0, 10)
    )

    buttons = tk.Frame(
        content,
        bg="#111111"
    )

    buttons.pack(
        fill="x",
        side="bottom",
        pady=(10, 20)
    )

    def test_connection():

        settings_status.configure(
            text="Testing connection..."
        )

        test_button.configure(
            state="disabled",
            bg=BUTTON_DISABLED
        )

        def worker():

            try:

                test_ai = AIProvider()

                result = test_ai.test_connection()

                if isinstance(result, tuple):

                    success, message = result

                else:

                    success = True
                    message = str(result)

            except Exception as e:

                success = False
                message = str(e)

            root.after(
                0,
                lambda: finish_test(
                    success,
                    message
                )
            )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def finish_test(success, message):

        try:

            if success:

                settings_status.configure(
                    text="Connection successful",
                    fg="#7CFF8A"
                )

            else:

                settings_status.configure(
                    text=f"Connection failed: {message}",
                    fg="#FF7777"
                )

            test_button.configure(
                state="normal",
                bg=BUTTON_COLOR
            )

        except tk.TclError:
            pass

    def save_settings():

        provider = provider_var.get().strip()
        model = model_var.get().strip()
        base_url = base_url_var.get().strip()
        api_key = api_key_var.get().strip()

        try:

            ai.save(
                provider,
                model,
                base_url,
                api_key
            )

            settings_status.configure(
                text="Settings saved",
                fg="#7CFF8A"
            )

            root.after(
                700,
                close_settings
            )

        except Exception as e:

            settings_status.configure(
                text=f"Save failed: {e}",
                fg="#FF7777"
            )

    test_button = tk.Button(
        buttons,
        text="Test Connection",
        bg=BUTTON_COLOR,
        fg=TEXT_COLOR,
        activebackground=BUTTON_HOVER,
        activeforeground=TEXT_COLOR,
        font=("Segoe UI", 9),
        bd=0,
        relief="flat",
        padx=16,
        pady=9,
        cursor="hand2",
        command=test_connection
    )

    test_button.pack(
        side="left"
    )

    save_button = tk.Button(
        buttons,
        text="Save",
        bg="#FFFFFF",
        fg="#000000",
        activebackground="#DDDDDD",
        activeforeground="#000000",
        font=("Segoe UI", 9, "bold"),
        bd=0,
        relief="flat",
        padx=24,
        pady=9,
        cursor="hand2",
        command=save_settings
    )

    save_button.pack(
        side="right"
    )

    add_hover(
        test_button,
        BUTTON_COLOR,
        BUTTON_HOVER
    )

    add_hover(
        save_button,
        "#FFFFFF",
        "#DDDDDD"
    )


# ============================================================
# AI PROCESSING
# ============================================================

def process_ai_request(
    user_message,
    chat_snapshot,
    first_interaction
):

    try:

        response = ai.chat(
            build_messages(chat_snapshot),
            temperature=0.7
        )

        if not response:
            response = "I didn't receive a response from the AI."

        title = None

        if first_interaction:

            title = generate_chat_title(
                user_message
            )

        safe_facts = extract_facts(
            chat_snapshot,
            user_message
        )

        private_facts = []

        if contains_private_information(user_message):
            private_facts.append(
                "Private information detected and not saved."
            )

        root.after(
            0,
            finish_ai_request,
            response,
            title,
            safe_facts,
            private_facts
        )

    except Exception as e:

        error_message = (
            f"AI connection error: "
            f"{type(e).__name__}: {e}"
        )

        root.after(
            0,
            finish_ai_request,
            error_message,
            None,
            [],
            []
        )


def finish_ai_request(
    response,
    title,
    safe_facts,
    private_facts
):

    global pending_private_facts

    if not root.winfo_exists():
        return

    chat = get_active_chat()

    chat["messages"].append({
        "role": "assistant",
        "content": response
    })

    if title:

        chat["title"] = title

    elif chat.get("title") == "New Chat":

        first = get_first_user_message(chat)

        if first:
            chat["title"] = fallback_chat_title(first)

    if safe_facts:
        add_safe_memory(safe_facts)

    pending_private_facts = private_facts

    display_message(
        "assistant",
        response
    )

    update_chat_header()
    update_history()

    save_memory()

    set_processing(False)


# ============================================================
# SEND MESSAGE
# ============================================================

def send_message(event=None):

    if is_processing:
        return "break"

    message = input_box.get(
        "1.0",
        tk.END
    ).strip()

    if not message:
        return "break"

    input_box.delete(
        "1.0",
        tk.END
    )

    # Commands
    command = message.lower().strip()

    if command == "/exit" or command == "/quit":

        root.destroy()
        return "break"

    if command == "/help":

        display_message(
            "user",
            message
        )

        display_message(
            "assistant",
            "Commands:\n"
            "/help - Show commands\n"
            "/memory - Show saved memory\n"
            "/clear - Clear this chat\n"
            "/forget - Forget saved memory\n"
            "/exit - Exit Jarvis"
        )

        return "break"

    if command == "/memory":

        display_message(
            "user",
            message
        )

        if memory.get("facts"):

            response = "Saved memory:\n\n" + "\n".join(
                f"• {fact}"
                for fact in memory["facts"]
            )

        else:

            response = "No saved memory."

        display_message(
            "assistant",
            response
        )

        return "break"

    if command == "/clear":

        clear_current_chat()

        return "break"

    if command == "/forget":

        forget_memory()

        display_message(
            "assistant",
            "Saved memory has been cleared."
        )

        return "break"

    chat = get_active_chat()

    first_interaction = not bool(
        chat.get("messages")
    )

    # --------------------------------------------------------
    # Add user message
    # --------------------------------------------------------

    chat["messages"].append({
        "role": "user",
        "content": message
    })

    # --------------------------------------------------------
    # Give immediate local title
    # --------------------------------------------------------

    if first_interaction:

        if contains_blocked_information(message):

            chat["title"] = "Private Interaction"

        else:

            chat["title"] = fallback_chat_title(
                message
            )

        update_chat_header()
        update_history()

    display_message(
        "user",
        message
    )

    save_memory()

    # --------------------------------------------------------
    # Snapshot before background thread
    # --------------------------------------------------------

    snapshot = {
        "id": chat["id"],
        "title": chat["title"],
        "messages": list(chat["messages"])
    }

    set_processing(True)

    threading.Thread(
        target=process_ai_request,
        args=(
            message,
            snapshot,
            first_interaction
        ),
        daemon=True
    ).start()

    return "break"


# ============================================================
# INPUT HANDLING
# ============================================================

def shift_enter(event):

    input_box.insert(
        tk.INSERT,
        "\n"
    )

    return "break"


def normal_enter(event):

    return send_message(event)


# ============================================================
# WINDOW CLOSE
# ============================================================

def on_close():

    try:
        save_memory()
    except Exception:
        pass

    root.destroy()


# ============================================================
# BUILD UI
# ============================================================

load_memory()

root = tk.Tk()

root.title(APP_TITLE)

root.geometry(
    "1100x720"
)

root.minsize(
    800,
    550
)

root.configure(
    bg=BG_COLOR
)

root.protocol(
    "WM_DELETE_WINDOW",
    on_close
)

# ============================================================
# ROOT GRID
# ============================================================

root.grid_rowconfigure(
    1,
    weight=1
)

root.grid_columnconfigure(
    1,
    weight=1
)


# ============================================================
# HEADER
# ============================================================

header = tk.Frame(
    root,
    bg=BG_COLOR,
    height=52
)

header.grid(
    row=0,
    column=0,
    columnspan=2,
    sticky="ew"
)

header.grid_propagate(False)

header.grid_columnconfigure(
    1,
    weight=1
)

menu_button = tk.Button(
    header,
    text="☰",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    activebackground="#181818",
    activeforeground=TEXT_COLOR,
    font=("Segoe UI Symbol", 15),
    bd=0,
    relief="flat",
    cursor="hand2",
    command=toggle_sidebar
)

menu_button.grid(
    row=0,
    column=0,
    padx=(12, 6),
    pady=8
)

chat_title_label = tk.Label(
    header,
    text="New Chat",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    font=("Segoe UI", 11, "bold"),
    anchor="w"
)

chat_title_label.grid(
    row=0,
    column=1,
    sticky="w",
    padx=8
)

status_label = tk.Label(
    header,
    text="Ready",
    bg=BG_COLOR,
    fg=SECONDARY_TEXT,
    font=("Segoe UI", 8)
)

status_label.grid(
    row=0,
    column=2,
    padx=18
)


# ============================================================
# SIDEBAR
# ============================================================

sidebar = tk.Frame(
    root,
    bg=SIDEBAR_COLOR,
    width=SIDEBAR_WIDTH
)

sidebar.grid(
    row=1,
    column=0,
    sticky="nsw"
)

sidebar.grid_propagate(False)

sidebar.grid_rowconfigure(
    2,
    weight=1
)


# Sidebar title

recent_header = tk.Label(
    sidebar,
    text="Recent Interactions",
    bg=SIDEBAR_COLOR,
    fg=TEXT_COLOR,
    font=("Segoe UI", 10, "bold"),
    anchor="w"
)

recent_header.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=14,
    pady=(16, 10)
)


# ============================================================
# NEW CHAT BUTTON
# ============================================================

new_chat_button = tk.Button(
    sidebar,
    text="＋  New Chat",
    bg=BUTTON_COLOR,
    fg=TEXT_COLOR,
    activebackground=BUTTON_HOVER,
    activeforeground=TEXT_COLOR,
    font=("Segoe UI", 9),
    bd=0,
    relief="flat",
    anchor="w",
    padx=12,
    cursor="hand2",
    command=new_chat
)

new_chat_button.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=10,
    pady=(0, 8),
    ipady=7
)

add_hover(
    new_chat_button,
    BUTTON_COLOR,
    BUTTON_HOVER
)


# ============================================================
# HISTORY
# ============================================================

history_container = tk.Frame(
    sidebar,
    bg=SIDEBAR_COLOR
)

history_container.grid(
    row=2,
    column=0,
    sticky="nsew",
    padx=0,
    pady=0
)

history_canvas = tk.Canvas(
    history_container,
    bg=SIDEBAR_COLOR,
    highlightthickness=0,
    bd=0
)

history_scrollbar = tk.Scrollbar(
    history_container,
    orient="vertical",
    command=history_canvas.yview,
    width=5,
    bd=0,
    highlightthickness=0,
    relief="flat",
    bg="#222222",
    troughcolor=SIDEBAR_COLOR,
    activebackground="#444444"
)

history_canvas.configure(
    yscrollcommand=history_scrollbar.set
)

history_canvas.pack(
    side="left",
    fill="both",
    expand=True
)

history_scrollbar.pack(
    side="right",
    fill="y"
)

history_frame = tk.Frame(
    history_canvas,
    bg=SIDEBAR_COLOR
)

history_window = history_canvas.create_window(
    (0, 0),
    window=history_frame,
    anchor="nw"
)


def update_history_scroll():

    history_canvas.configure(
        scrollregion=history_canvas.bbox("all")
    )


def resize_history_frame(event):

    history_canvas.itemconfigure(
        history_window,
        width=event.width
    )


history_frame.bind(
    "<Configure>",
    lambda event: update_history_scroll()
)

history_canvas.bind(
    "<Configure>",
    resize_history_frame
)


# ============================================================
# SIDEBAR BOTTOM
# ============================================================

sidebar_bottom = tk.Frame(
    sidebar,
    bg=SIDEBAR_COLOR
)

sidebar_bottom.grid(
    row=3,
    column=0,
    sticky="ew",
    padx=10,
    pady=10
)

settings_button = tk.Button(
    sidebar_bottom,
    text="⚙  Settings",
    bg=SIDEBAR_COLOR,
    fg="#BDBDBD",
    activebackground="#1A1A1A",
    activeforeground=TEXT_COLOR,
    font=("Segoe UI", 9),
    bd=0,
    relief="flat",
    anchor="w",
    padx=8,
    cursor="hand2",
    command=open_settings
)

settings_button.pack(
    fill="x",
    ipady=7
)

add_hover(
    settings_button,
    SIDEBAR_COLOR,
    "#181818"
)


# ============================================================
# MAIN AREA
# ============================================================

main_area = tk.Frame(
    root,
    bg=CHAT_COLOR
)

main_area.grid(
    row=1,
    column=1,
    sticky="nsew"
)

main_area.grid_rowconfigure(
    0,
    weight=1
)

main_area.grid_rowconfigure(
    1,
    weight=0
)

main_area.grid_columnconfigure(
    0,
    weight=1
)


# ============================================================
# CHAT AREA
# ============================================================

chat_container = tk.Frame(
    main_area,
    bg=CHAT_COLOR
)

chat_container.grid(
    row=0,
    column=0,
    sticky="nsew"
)

chat_container.grid_rowconfigure(
    0,
    weight=1
)

chat_container.grid_columnconfigure(
    0,
    weight=1
)

chat_canvas = tk.Canvas(
    chat_container,
    bg=CHAT_COLOR,
    highlightthickness=0,
    bd=0
)

chat_canvas.grid(
    row=0,
    column=0,
    sticky="nsew"
)

chat_scrollbar = tk.Scrollbar(
    chat_container,
    orient="vertical",
    command=chat_canvas.yview,
    width=6,
    bd=0,
    highlightthickness=0,
    relief="flat",
    bg="#252525",
    troughcolor=CHAT_COLOR,
    activebackground="#444444"
)

chat_scrollbar.grid(
    row=0,
    column=1,
    sticky="ns"
)

chat_canvas.configure(
    yscrollcommand=chat_scrollbar.set
)

messages_frame = tk.Frame(
    chat_canvas,
    bg=CHAT_COLOR
)

messages_window = chat_canvas.create_window(
    (0, 0),
    window=messages_frame,
    anchor="nw"
)


def update_chat_scroll():

    chat_canvas.configure(
        scrollregion=chat_canvas.bbox("all")
    )


def resize_messages_frame(event):

    chat_canvas.itemconfigure(
        messages_window,
        width=event.width
    )


messages_frame.bind(
    "<Configure>",
    lambda event: update_chat_scroll()
)

chat_canvas.bind(
    "<Configure>",
    resize_messages_frame
)


# ============================================================
# INPUT AREA
# ============================================================

input_area = tk.Frame(
    main_area,
    bg=CHAT_COLOR
)

input_area.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=18,
    pady=(8, 16)
)

input_area.grid_columnconfigure(
    0,
    weight=1
)

input_box = tk.Text(
    input_area,
    height=3,
    bg=INPUT_COLOR,
    fg=TEXT_COLOR,
    insertbackground=TEXT_COLOR,
    selectbackground="#333333",
    selectforeground=TEXT_COLOR,
    font=("Segoe UI", 10),
    wrap="word",
    relief="flat",
    bd=0,
    padx=12,
    pady=10
)

input_box.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=(0, 8)
)


# Buttons container

input_buttons = tk.Frame(
    input_area,
    bg=CHAT_COLOR
)

input_buttons.grid(
    row=0,
    column=1,
    sticky="ns"
)


send_button = tk.Button(
    input_buttons,
    text="Send",
    bg=BUTTON_COLOR,
    fg=TEXT_COLOR,
    activebackground=BUTTON_HOVER,
    activeforeground=TEXT_COLOR,
    font=("Segoe UI", 9, "bold"),
    bd=0,
    relief="flat",
    cursor="hand2",
    command=send_message,
    padx=18
)

send_button.pack(
    fill="x",
    pady=(0, 4),
    ipady=7
)

add_hover(
    send_button,
    BUTTON_COLOR,
    BUTTON_HOVER
)


new_chat_bottom_button = tk.Button(
    input_buttons,
    text="New Chat",
    bg=BUTTON_COLOR,
    fg=SECONDARY_TEXT,
    activebackground=BUTTON_HOVER,
    activeforeground=TEXT_COLOR,
    font=("Segoe UI", 8),
    bd=0,
    relief="flat",
    cursor="hand2",
    command=new_chat
)

new_chat_bottom_button.pack(
    fill="x",
    pady=2,
    ipady=5
)

add_hover(
    new_chat_bottom_button,
    BUTTON_COLOR,
    BUTTON_HOVER
)


clear_button = tk.Button(
    input_buttons,
    text="Clear",
    bg=BUTTON_COLOR,
    fg=SECONDARY_TEXT,
    activebackground=BUTTON_HOVER,
    activeforeground=TEXT_COLOR,
    font=("Segoe UI", 8),
    bd=0,
    relief="flat",
    cursor="hand2",
    command=clear_current_chat
)

clear_button.pack(
    fill="x",
    pady=2,
    ipady=5
)

add_hover(
    clear_button,
    BUTTON_COLOR,
    BUTTON_HOVER
)


forget_button = tk.Button(
    input_buttons,
    text="Forget",
    bg=BUTTON_COLOR,
    fg=SECONDARY_TEXT,
    activebackground=BUTTON_HOVER,
    activeforeground=TEXT_COLOR,
    font=("Segoe UI", 8),
    bd=0,
    relief="flat",
    cursor="hand2",
    command=forget_memory
)

forget_button.pack(
    fill="x",
    pady=(2, 0),
    ipady=5
)

add_hover(
    forget_button,
    BUTTON_COLOR,
    BUTTON_HOVER
)


# ============================================================
# KEYBOARD
# ============================================================

input_box.bind(
    "<Return>",
    normal_enter
)

input_box.bind(
    "<Shift-Return>",
    shift_enter
)

input_box.bind(
    "<Control-Return>",
    normal_enter
)

root.bind(
    "<Escape>",
    lambda event: (
        close_settings(),
        close_delete_overlay(),
        close_chat_menu(),
        finish_inline_rename(cancel=True)
    )
)


# ============================================================
# MOUSE WHEEL
# ============================================================

def mousewheel_chat(event):

    try:

        chat_canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    except Exception:
        pass


chat_canvas.bind(
    "<MouseWheel>",
    mousewheel_chat
)


# ============================================================
# INITIAL UI
# ============================================================

update_history()
display_current_chat()

input_box.focus_set()

root.mainloop()