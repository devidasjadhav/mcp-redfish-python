import os
import getpass
from langchain_anthropic import ChatAnthropic

# Set API key
if "ANTHROPIC_API_KEY" not in os.environ:
    os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter your Anthropic API key: ")

# Instantiate model
model = ChatAnthropic(model="claude-3-5-haiku-20241022")

# Chat loop
messages = []
print("Chatbot ready! Type 'quit' or 'exit' to end the conversation.")

while True:
    user_input = input("You: ")
    if user_input.lower() in ['quit', 'exit']:
        break
    messages.append({"role": "user", "content": user_input})
    response = model.invoke(messages)
    print("Bot:", response.content)
    messages.append({"role": "assistant", "content": response.content})
