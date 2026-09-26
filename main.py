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

    except OSError as error:
        print("Could not save memory:", error)

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

#Show available commands
def show_help():
    print("""
Commands:
/help   -   Show available commands
/memory  -  Show memory information
/clear   -  Clear conversation memory
/forget  -  Clear long-term memory
/exit   -   Exit the assistant
""")

#Show memory information
def show_memory(memory):
    print()
    print("Memory:")

    print("Long-term memory:")

    if memory["facts"]:
        for index, fact in enumerate(memory["facts"], 1):
            print(f"{index}. {fact}")
    else:
        print("No long-term memories saved.")

    print()
    print(f"Conversation messages: {len(memory['conversation'])}")
    print()

#Clear conversation memory
def clear_memory(memory):
    memory["conversation"] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

#Clear long-term memory
def clear_facts(memory):
    memory["facts"] = []

#Start assistant
memory = load_memory()

print("Jarvis is ready. [/help for commands | /exit or /quit to quit]")

#Start chat loop
while True:
    try:
        message = input("You: ").strip()

        #Ignore empty messages
        if not message:
            continue

        #Handle help command
        if message.lower() == "/help":
            show_help()
            continue

        #Handle memory command
        if message.lower() == "/memory":
            show_memory(memory)
            continue

        #Handle clear command
        if message.lower() == "/clear":
            clear_memory(memory)
            save_memory(memory)
            print("Memory cleared.\n")
            continue

        #Handle forget command
        if message.lower() == "/forget":
            clear_facts(memory)
            save_memory(memory)
            print("Long-term memory cleared.\n")
            continue

        #Handle exit command
        if message.lower() in ["/exit", "exit", "quit"]:
            save_memory(memory)
            print("AI: Goodbye!")
            break

        #Add user message
        memory["conversation"].append({
            "role": "user",
            "content": message
        })

        #Build conversation with long-term memory
        messages = build_messages(memory)

        #Send conversation to Ollama
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )

        #Get AI response
        answer = response.choices[0].message.content

        #Add AI response to memory
        memory["conversation"].append({
            "role": "assistant",
            "content": answer
        })

        #Extract important facts
        extract_facts(memory)

        #Save memory
        save_memory(memory)

        #Display AI response 
        print("AI:", answer)
        print()

    except KeyboardInterrupt:
        save_memory(memory)
        print("\nAI: Goodbye!")
        break

    except Exception as error:
        print()
        print("Error:", error)
        print()