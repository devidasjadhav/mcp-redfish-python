import os
import getpass
from langchain_anthropic import ChatAnthropic
from langchain.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from .redfish_tool import list_endpoints, get_endpoint_data, patch_resource, post_action

# Set API key
if "ANTHROPIC_API_KEY" not in os.environ:
    os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter your Anthropic API key: ")

# Instantiate model with tools
model = ChatAnthropic(model="claude-3-5-haiku-20241022")
model_with_tools = model.bind_tools([list_endpoints, get_endpoint_data, patch_resource, post_action])

def run_chatbot():
    # Chat loop
    messages = []
    messages.append(SystemMessage(content="You are an intelligent Redfish control agent. Analyze user requests, determine appropriate Redfish operations, and use the available tools to execute them. Always discover capabilities first if needed. Be helpful and explain your actions."))
    print("Intelligent Redfish Chatbot ready! Type 'quit' or 'exit' to end the conversation.")
    print("I can help with Redfish server management using intelligent reasoning.")

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
                elif tool_call["name"] == "patch_resource":
                    result = patch_resource.invoke(tool_call["args"])
                elif tool_call["name"] == "post_action":
                    result = post_action.invoke(tool_call["args"])
                else:
                    result = "Unknown tool"
                tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

            # Add tool results and invoke again
            messages.extend(tool_messages)
            response = model_with_tools.invoke(messages)
            messages.append(response)

        print("Bot:", response.content)

if __name__ == "__main__":
    run_chatbot()
