
from openai import OpenAI
import json
import os


#Ollama
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

MODEL = "qwen2.5-coder:7b"
MEMORY_FILE = "memory.json"



# Load previous conversation
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            pass

    return [
        {
                        "role": "system",
                        "content": """
            You are my personal AI assistant.

            Be helpful, friendly, and conversational.

            Explain technical concepts clearly and simply.

            Help me write, understand, and debug code.

            When something is difficult, use simple examples.

            If I make a mistake, explain what went wrong and how to fix it.

            Keep responses reasonably concise unless I ask for a detailed explanation.
            """
        }
    ]



# Save conversation

def save_memory(messages):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump(messages, file, indent=2, ensure_ascii=False)
    except OSError as error:
        print("Could not save memory:", error)



# Start assistant
messages = load_memory()

print("Ready.\n")



# Chat loop
while True:
    try:
        message = input("You: ").strip()

        # Exit
        if message.lower() in ["exit", "quit"]:
            save_memory(messages)
            print("AI: Goodbye!")
            break

        # Ignore empty messages
        if not message:
            continue

        # Add user message
        messages.append({
            "role": "user",
            "content": message
        })

        # Ask Ollama
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )

        answer = response.choices[0].message.content

        # Add AI response
        messages.append({
            "role": "assistant",
            "content": answer
        })

        # Save immediately
        save_memory(messages)

        print()
        print("AI:", answer)
        print()

    except KeyboardInterrupt:
        save_memory(messages)
        print("\nAI: Goodbye!")
        break

    except Exception as error:
        print()
        print("Error:", error)
        print()

