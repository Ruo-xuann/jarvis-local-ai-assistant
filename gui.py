import tkinter as tk
from tkinter import scrolledtext
from openai import OpenAI
import json
import os

#Ollama connection
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

MODEL = "qwen2.5-coder:7b"
MEMORY_FILE = "memory.json"

#System prompt
SYSTEM_PROMPT = """
                    You are my personal AI assistant.

                    Be helpful, friendly, and conversational.

                    Explain technical concepts clearly and simply.

                    Help me write, understand, and debug code.

                    When something is difficult, use simple examples.

                    If I make a mistake, explain what went wrong and how to fix it.

                    Keep responses reasonably concise unless I ask for a detailed explanation.

                    Use the long-term memory provided to you when it is relevant.
                """

#Load memory
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                memory = json.load(file)

            if "conversation" in memory and "facts" in memory:
                return memory

        except (json.JSONDecodeError, OSError):
            pass

    return {
        "conversation": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ],
        "facts": []
    }

#Save memory
def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump(memory, file, indent=2, ensure_ascii=False)

    except OSError:
        pass

#Build messages for AI
def build_messages(memory):
    messages = memory["conversation"].copy()

    if memory["facts"]:
        facts_text = "\n".join(
            f"- {fact}" for fact in memory["facts"]
        )

        memory_message = {
            "role": "system",
            "content": f"""
Long-term memory about the user:

{facts_text}

Use these facts only when relevant.
"""
        }

        messages.insert(1, memory_message)

    return messages

#Extract important facts
def extract_facts(memory):
    conversation = memory["conversation"]

    if len(conversation) < 3:
        return

    recent_messages = conversation[-6:]

    conversation_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in recent_messages
        if message["role"] != "system"
    )

    prompt = f"""
Analyze this conversation and identify important facts about the user
that would be useful to remember in future conversations.

Only save stable or useful information such as:
- Preferences
- Long-term projects
- Programming languages or technologies they use
- Important workflow preferences
- Things they explicitly want the assistant to remember

Do NOT save:
- Temporary questions
- Passwords
- API keys
- Personal secrets
- Sensitive information
- Random conversation details

Return ONLY a JSON array of short strings.

Example:
["User prefers concise explanations", "User is building a Python AI assistant"]

Conversation:
{conversation_text}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response.choices[0].message.content.strip()

        if result.startswith("```"):
            result = result.replace("```json", "")
            result = result.replace("```", "")
            result = result.strip()

        new_facts = json.loads(result)

        if isinstance(new_facts, list):
            for fact in new_facts:
                if isinstance(fact, str) and fact.strip():
                    if fact not in memory["facts"]:
                        memory["facts"].append(fact.strip())

    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    except Exception:
        pass

#Display message
def display_message(sender, message):
    chat_box.config(state=tk.NORMAL)
    chat_box.insert(tk.END, f"{sender}: {message}\n\n")
    chat_box.config(state=tk.DISABLED)
    chat_box.see(tk.END)

#Send message
def send_message(event=None):
    message = message_entry.get().strip()

    if not message:
        return

    message_entry.delete(0, tk.END)

    #Handle commands
    if message.lower() == "/clear":
        clear_conversation()
        return

    if message.lower() == "/forget":
        forget_memory()
        return

    if message.lower() == "/memory":
        show_memory()
        return

    if message.lower() == "/help":
        show_help()
        return

    if message.lower() in ["/exit", "exit", "quit"]:
        root.destroy()
        return

    display_message("You", message)

    memory["conversation"].append({
        "role": "user",
        "content": message
    })

    send_button.config(state=tk.DISABLED)
    message_entry.config(state=tk.DISABLED)

    root.update_idletasks()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=build_messages(memory)
        )

        answer = response.choices[0].message.content

        memory["conversation"].append({
            "role": "assistant",
            "content": answer
        })

        extract_facts(memory)
        save_memory(memory)

        display_message("AI", answer)

    except Exception as error:
        display_message("Error", str(error))

    finally:
        send_button.config(state=tk.NORMAL)
        message_entry.config(state=tk.NORMAL)
        message_entry.focus()

#Clear conversation
def clear_conversation():
    memory["conversation"] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    save_memory(memory)

    chat_box.config(state=tk.NORMAL)
    chat_box.delete("1.0", tk.END)
    chat_box.config(state=tk.DISABLED)

    display_message("AI", "Conversation cleared.")

#Show memory
def show_memory():
    chat_box.config(state=tk.NORMAL)

    chat_box.insert(tk.END, "Long-term memory:\n\n")

    if memory["facts"]:
        for index, fact in enumerate(memory["facts"], 1):
            chat_box.insert(tk.END, f"{index}. {fact}\n")
    else:
        chat_box.insert(tk.END, "No long-term memories saved.\n")

    chat_box.insert(tk.END, "\n")
    chat_box.config(state=tk.DISABLED)
    chat_box.see(tk.END)

#Forget memory
def forget_memory():
    memory["facts"] = []
    save_memory(memory)

    display_message("AI", "Long-term memory cleared.")

#Show help
def show_help():
    help_text = """
Commands:

/help    - Show available commands
/memory  - Show long-term memory
/clear   - Clear conversation
/forget  - Clear long-term memory
/exit    - Exit Jarvis
"""

    display_message("AI", help_text)

#Load memory
memory = load_memory()

#Create window
root = tk.Tk()
root.title("Jarvis")
root.geometry("900x600")
root.minsize(600, 400)

#Title
title_label = tk.Label(
    root,
    text="Jarvis",
    font=("Arial", 18, "bold")
)

title_label.pack(pady=10)

#Chat area
chat_box = scrolledtext.ScrolledText(
    root,
    wrap=tk.WORD,
    font=("Arial", 11),
    state=tk.DISABLED
)

chat_box.pack(
    fill=tk.BOTH,
    expand=True,
    padx=15,
    pady=5
)

#Input area
input_frame = tk.Frame(root)
input_frame.pack(
    fill=tk.X,
    padx=15,
    pady=10
)

message_entry = tk.Entry(
    input_frame,
    font=("Arial", 11)
)

message_entry.pack(
    side=tk.LEFT,
    fill=tk.X,
    expand=True,
    ipady=8
)

send_button = tk.Button(
    input_frame,
    text="Send",
    width=10,
    command=send_message
)

send_button.pack(
    side=tk.RIGHT,
    padx=(10, 0)
)

#Button area
button_frame = tk.Frame(root)
button_frame.pack(pady=(0, 10))

clear_button = tk.Button(
    button_frame,
    text="Clear",
    width=12,
    command=clear_conversation
)

clear_button.pack(
    side=tk.LEFT,
    padx=5
)

memory_button = tk.Button(
    button_frame,
    text="Memory",
    width=12,
    command=show_memory
)

memory_button.pack(
    side=tk.LEFT,
    padx=5
)

forget_button = tk.Button(
    button_frame,
    text="Forget Memory",
    width=15,
    command=forget_memory
)

forget_button.pack(
    side=tk.LEFT,
    padx=5
)

#Enter key sends message
message_entry.bind(
    "<Return>",
    send_message
)

#Focus input
message_entry.focus()

#Start GUI
root.mainloop()