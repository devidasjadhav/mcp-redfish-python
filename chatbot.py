import os
import getpass
from langchain_anthropic import ChatAnthropic
from langchain.messages import HumanMessage, AIMessage, ToolMessage
from redfish_tool import list_endpoints, get_endpoint_data

# Set API key
if "ANTHROPIC_API_KEY" not in os.environ:
    os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter your Anthropic API key: ")

# Instantiate model with tools
model = ChatAnthropic(model="claude-3-5-haiku-20241022")
model_with_tools = model.bind_tools([list_endpoints, get_endpoint_data])

# Chat loop
messages = []
print("Chatbot ready! Type 'quit' or 'exit' to end the conversation.")
print("You can ask about Redfish endpoints and server information.")

while True:
    user_input = input("You: ")
    if user_input.lower() in ['quit', 'exit']:
        break
    messages.append(HumanMessage(content=user_input))

    # Invoke model
    response = model_with_tools.invoke(messages)
    messages.append(response)

    # Handle tool calls
    while response.tool_calls:
        tool_messages = []
        for tool_call in response.tool_calls:
            if tool_call["name"] == "list_endpoints":
                result = list_endpoints.invoke({})
            elif tool_call["name"] == "get_endpoint_data":
                result = get_endpoint_data.invoke(tool_call["args"])
            else:
                result = "Unknown tool"
            tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

        # Add tool results and invoke again
        messages.extend(tool_messages)
        response = model_with_tools.invoke(messages)
        messages.append(response)

    print("Bot:", response.content)
