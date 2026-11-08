"""Interactive LangChain chatbot for Redfish server management."""

from langchain_anthropic import ChatAnthropic
from langchain.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from .redfish_tool import (
    find_capabilities,
    get_endpoint_data,
    invoke_action,
    list_endpoints,
    set_properties,
)
from .config import config

TOOLS = [
    list_endpoints,
    get_endpoint_data,
    find_capabilities,
    set_properties,
    invoke_action,
]
TOOL_MAP = {item.name: item for item in TOOLS}


def _build_model_with_tools():
    """Create the Anthropic model and bind the Redfish tools.

    The model is built on demand so importing this module never requires an
    API key (for example while collecting tests) and never prompts for one.

    Returns:
        A LangChain chat model with the Redfish tools bound.

    Raises:
        ValueError: If the configuration is invalid, including when
            ANTHROPIC_API_KEY is missing.
    """
    errors = config.validate()
    if errors:
        raise ValueError("Invalid configuration: " + "; ".join(errors))
    model = ChatAnthropic(
        model=config.ANTHROPIC_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
    )
    return model.bind_tools(TOOLS)


def run_chatbot():
    model_with_tools = _build_model_with_tools()

    # Chat loop
    messages = []
    messages.append(SystemMessage(content=(
        "You are an intelligent Redfish control agent. Never construct raw HTTP "
        "write bodies. Use find_capabilities, set_properties, and invoke_action. "
        "Supply selectors inferred from conversation context first. If a result "
        "is ambiguous, refine selectors from context; ask the user to choose a "
        "candidate only as a last resort. Never select the first candidate "
        "arbitrarily."
    )))
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
                selected_tool = TOOL_MAP.get(tool_call["name"])
                result = (
                    selected_tool.invoke(tool_call["args"])
                    if selected_tool
                    else "Unknown tool"
                )
                tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

            # Add tool results and invoke again
            messages.extend(tool_messages)
            response = model_with_tools.invoke(messages)
            messages.append(response)

        print("Bot:", response.content)

if __name__ == "__main__":
    try:
        run_chatbot()
    except ValueError as error:
        raise SystemExit(f"Configuration error: {error}") from error
