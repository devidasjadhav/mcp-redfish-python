# Redfish MCP Project

An intelligent Redfish server management system using Model Context Protocol (MCP) and AI-powered chatbots.

## Overview

This project provides an AI-powered interface for managing Redfish-enabled servers through natural language commands. It includes:

- **Chatbot Interface**: Interactive AI assistant for Redfish operations
- **MCP Server**: Model Context Protocol server for tool integration
- **Redfish Tools**: Direct API tools for Redfish operations
- **Mock Server**: Testing environment for development

## Quick Start

1. **Set up Redfish Mock Server** (see [User Guide](#user-guide) for details)
2. **Install dependencies** and set API key
3. **Start MCP Server** and **run Chatbot**

## Project Structure

```
├── src/
│   └── redfish_mcp/          # Main source code package
│       ├── __init__.py       # Package initialization
│       ├── chatbot.py        # AI-powered chatbot interface
│       ├── redfish_mcp_server.py  # MCP server implementation
│       └── redfish_tool.py   # Redfish API tool functions
├── tests/                    # Test files
│   └── test_chatbot.py       # Chatbot functionality tests
├── docs/                     # Documentation
│   ├── DSP0266_1.23.0.md     # Redfish specification docs
│   └── DSP0268_2025.3.md     # Additional Redfish docs
├── scripts/                  # Utility scripts
│   └── mock_redfish_server.py  # Mock Redfish server for testing
├── AGENTS.md                 # Development guidelines for AI agents
└── README.md                 # This file
```

## User Guide

### Prerequisites

- Python 3.8+
- Anthropic API key (for chatbot functionality)
- Redfish Mockup Server (for testing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd redfish-mcp-project
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Copy the example configuration
   cp .env.example .env

   # Edit .env with your settings
   nano .env  # or your preferred editor
   ```

4. **Set required API key**
   ```bash
   # Either in .env file or environment variable
   export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
   ```

### Setting up Redfish Mock Server

For testing purposes, use the official DMTF Redfish Mockup Server:

1. **Clone the Redfish Mockup Server**
   ```bash
   git clone https://github.com/DMTF/Redfish-Mockup-Server.git
   cd Redfish-Mockup-Server
   ```

2. **Start the mock server**
   ```bash
   python3 redfishMockupServer.py -D public-rackmount1 -S
   ```

   This starts the server on `http://localhost:8000` with the `public-rackmount1` mockup data.

### Running the System

#### 1. Start MCP Server

The MCP server provides tool integration capabilities:

```bash
cd /path/to/redfish-mcp-project
PYTHONPATH=. python3 -m src.redfish_mcp.redfish_mcp_server
```

You should see output like:
```
╭─ FastMCP 2.0 ──────────────────────────────────────────────────────────────╮
│                                                                            │
│        _ __ ___ ______           __  __  _____________    ____    ____     │
│       _ __ ___ / ____/___ ______/ /_/  |/  / ____/ __ \  |___ \  / __ \    │
│      _ __ ___ / /_  / __ `/ ___/ __/ /|_/ / /   / /_/ /  ___/ / / / / /    │
│     _ __ ___ / __/ / /_/ (__  ) /_/ /  / / /___/ ____/  /  __/_/ /_/ /     │
│    _ __ ___ /_/    \__,_/____/\__/_/  /_/\____/_/      /_____(_)____/      │
│                                                                            │
│                                                                            │
│                                                                            │
│    🖥️  Server name:     Redfish MCP Server                                  │
│    📦 Transport:       STDIO                                               │
│                                                                            │
│    📚 Docs:            https://gofastmcp.com                               │
│    🚀 Deploy:          https://fastmcp.cloud                               │
│                                                                            │
│    🏎️  FastMCP version: 2.11.3                                              │
│    🤝 MCP version:     1.12.4                                              │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯

[12/13/25 23:30:30] INFO     Starting MCP server 'Redfish MCP Server' with transport 'stdio'
```

#### 2. Run the Chatbot

In a separate terminal, start the AI-powered chatbot:

```bash
cd /path/to/redfish-mcp-project
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
PYTHONPATH=. python3 -m src.redfish_mcp.chatbot
```

**Example interaction:**
```
Intelligent Redfish Chatbot ready! Type 'quit' or 'exit' to end the conversation.
I can help with Redfish server management using intelligent reasoning.

You: List the available Redfish endpoints

Bot: I'll help you list the available Redfish endpoints. Let me query the service root.

[Tool Call: list_endpoints]
Available Redfish endpoints from http://127.0.0.1:8000/redfish/v1:
- AccountService: /redfish/v1/AccountService
- CertificateService: /redfish/v1/CertificateService
- Chassis: /redfish/v1/Chassis
- ComponentIntegrity: /redfish/v1/ComponentIntegrity
- EventService: /redfish/v1/EventService
- KeyService: /redfish/v1/KeyService
- Managers: /redfish/v1/Managers
- Registries: /redfish/v1/Registries
- SessionService: /redfish/v1/SessionService
- Systems: /redfish/v1/Systems
- Tasks: /redfish/v1/TaskService
- UpdateService: /redfish/v1/UpdateService

You: Tell me about the systems

Bot: The user is asking about systems. I should query the Systems endpoint to get information about the computer systems available.

[Tool Call: get_endpoint_data]
{"@odata.id": "/redfish/v1/Systems", "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection", "Members": [{"@odata.id": "/redfish/v1/Systems/437XR1138R2"}], "Members@odata.count": 1, "Name": "Computer System Collection"}

You: quit
```

### Testing the Tools Directly

You can also test individual tools without the AI interface:

```bash
# List endpoints
PYTHONPATH=. python3 -c "from src.redfish_mcp.redfish_tool import list_endpoints; print(list_endpoints.invoke({}))"

# Get system information
PYTHONPATH=. python3 -c "from src.redfish_mcp.redfish_tool import get_endpoint_data; print(get_endpoint_data.invoke({'endpoint_url': '/Systems'}))"
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_chatbot.py
```

## Architecture Details (For Contributors)

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│   Chatbot AI     │───▶│   Tool Calls    │
│                 │    │  (Anthropic)     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Server    │◀──▶│   Tool Router    │───▶│  Redfish API    │
│  (FastMCP)      │    │                  │    │  (HTTP/REST)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Component Details

#### 1. RedfishClient (`src/redfish_mcp/client.py`)
- **Purpose**: Shared HTTP client for all Redfish operations
- **Technology**: Requests library with session management
- **Functionality**:
  - Centralized HTTP request handling
  - Error handling and response processing
  - URL building and validation
  - Connection pooling and timeout management

#### 2. Configuration (`src/redfish_mcp/config.py`)
- **Purpose**: Environment-based configuration management
- **Technology**: Python environment variables
- **Functionality**:
  - Redfish server settings (URL, timeout, SSL)
  - Authentication credentials (future)
  - AI model configuration
  - Logging settings (future)

#### 3. Chatbot (`src/redfish_mcp/chatbot.py`)
- **Purpose**: Natural language interface for Redfish operations
- **Technology**: LangChain + Anthropic Claude
- **Functionality**:
  - Processes user queries in natural language
  - Determines appropriate Redfish operations
  - Calls tools via MCP protocol
  - Maintains conversation context

#### 4. MCP Server (`src/redfish_mcp/redfish_mcp_server.py`)
- **Purpose**: Exposes Redfish tools via Model Context Protocol
- **Technology**: FastMCP framework
- **Functionality**:
  - Registers Redfish tools
  - Handles tool invocations
  - Manages communication with AI models

#### 5. Redfish Tools (`src/redfish_mcp/redfish_tool.py`)
- **Purpose**: LangChain tool wrappers for Redfish operations
- **Technology**: LangChain tools + RedfishClient
- **Available Tools**:
  - `list_endpoints()`: Discover available Redfish endpoints
  - `get_endpoint_data()`: Retrieve data from specific endpoints
  - `find_capabilities()`: Find writable properties/actions and candidate resources
  - `set_properties()`: Apply validated values to one resolved resource
  - `invoke_action()`: Invoke an action with validated parameters

Write tools never accept raw HTTP bodies or action URLs. The server follows
same-origin `@odata.id` links with read-only requests, learns a typed contract
for the target and Redfish role, and constructs PATCH/POST requests itself.
Storage, cache hits, and re-exploration are transparent to MCP clients.

When several resources expose the same property, selectors such as `Name`,
`Id`, resource type, interface kind, endpoint, or ancestor path are applied
first. If context still does not identify one resource, the tool returns
labeled candidates and performs no write. Retry with the selected
`candidate_id`; do not choose the first candidate automatically.

#### 6. Mock Server (`scripts/mock_redfish_server.py`)
- **Purpose**: Development and testing environment
- **Technology**: Flask web server
- **Functionality**: Provides mock Redfish API responses

### Data Flow

1. **User Query** → Chatbot receives natural language input
2. **AI Processing** → Claude analyzes query and determines tool calls
3. **Tool Execution** → MCP server routes calls to appropriate Redfish tools
4. **API Calls** → Tools make HTTP requests to Redfish endpoints
5. **Response** → Results flow back through MCP → AI → User

### Configuration

The application supports configuration through environment variables and `.env` files. Create a `.env` file from the provided template:

```bash
cp .env.example .env
```

#### Environment Variables

**Redfish Server Settings:**
- **REDFISH_BASE_URL**: Redfish server URL (default: `http://127.0.0.1:8000/redfish/v1`)
- **REQUEST_TIMEOUT**: HTTP request timeout in seconds (default: `30`)
- **VERIFY_SSL**: Whether to verify SSL certificates (default: `true`)

**Authentication:**
- **REDFISH_USERNAME**: Username for Redfish authentication (optional)
- **REDFISH_PASSWORD**: Password for Redfish authentication (optional)

**Learned contracts:**
- **CONTRACT_SQLITE_PATH**: Shared SQLite file (default: `.redfish_contracts.sqlite3`)
- **REDIS_URL**: Use Redis instead of SQLite when set
- **CONTRACT_PROBE_TTL_SECONDS**: Firmware/identity probe TTL (default: `30`)
- **CONTRACT_REFRESH_TTL_SECONDS**: Full topology refresh TTL (default: `300`)
- **CANDIDATE_TTL_SECONDS**: Ambiguous candidate lifetime (default: `300`)
- **EXPLORE_MAX_RESOURCES**: Maximum resources explored per call (default: `200`)
- **EXPLORE_MAX_DEPTH**: Maximum navigation depth (default: `8`)
- **EXPLORE_MAX_ACTIONS**: Maximum ActionInfo documents per resource (default: `16`)
- **MAX_RESPONSE_BYTES**: Maximum accepted response body (default: `1048576`)

SQLite is appropriate for processes sharing a filesystem. Set `REDIS_URL` for
instances on different hosts. Contracts are isolated by service UUID and role;
write audit records include the exact contract revision.

**Resilience Settings:**
- **ENABLE_RETRY**: Enable automatic retry with backoff (default: `true`)
- **ENABLE_CIRCUIT_BREAKER**: Enable circuit breaker protection (default: `true`)
- **MAX_RETRY_ATTEMPTS**: Maximum retry attempts (default: `3`)
- **RETRY_BASE_DELAY**: Base delay between retries in seconds (default: `1.0`)
- **RETRY_MAX_DELAY**: Maximum delay between retries in seconds (default: `30.0`)
- **CIRCUIT_BREAKER_THRESHOLD**: Failures before opening circuit (default: `5`)
- **CIRCUIT_BREAKER_TIMEOUT**: Recovery timeout in seconds (default: `60.0`)

**AI Configuration:**
- **ANTHROPIC_API_KEY**: Required for chatbot functionality
- **ANTHROPIC_MODEL**: Claude model to use (default: `claude-3-5-haiku-20241022`)

**Logging:**
- **LOG_LEVEL**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: `INFO`)
- **LOG_FILE**: Optional log file path

**MCP Server:**
- **MCP_SERVER_NAME**: Server display name (default: `Redfish MCP Server`)
- **MCP_SERVER_VERSION**: Server version (default: `1.0.0`)
- **MCP_TRANSPORT**: Transport protocol (default: `stdio`)

#### Configuration Validation

The application validates configuration on startup and will exit with clear error messages if required settings are missing or invalid.

#### Example .env file:
```bash
# Redfish Server Configuration
REDFISH_BASE_URL=http://your-redfish-server:8000/redfish/v1
REQUEST_TIMEOUT=30
VERIFY_SSL=true

# Authentication (leave empty if not required)
REDFISH_USERNAME=
REDFISH_PASSWORD=

# Learned Contract Storage (set REDIS_URL for multi-host deployments)
CONTRACT_SQLITE_PATH=.redfish_contracts.sqlite3
REDIS_URL=
CONTRACT_PROBE_TTL_SECONDS=30
CONTRACT_REFRESH_TTL_SECONDS=300
CANDIDATE_TTL_SECONDS=300
EXPLORE_MAX_RESOURCES=200
EXPLORE_MAX_DEPTH=8
EXPLORE_MAX_ACTIONS=16
MAX_RESPONSE_BYTES=1048576

# Resilience Configuration
ENABLE_RETRY=true
ENABLE_CIRCUIT_BREAKER=true
MAX_RETRY_ATTEMPTS=3
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=30.0
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60.0

# AI Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=

# MCP Server Configuration
MCP_SERVER_NAME=Redfish MCP Server
MCP_SERVER_VERSION=1.0.0
MCP_TRANSPORT=stdio
```

### Error Handling

- **Network Errors**: HTTP timeouts and connection failures
- **API Errors**: Invalid endpoints, authentication failures
- **JSON Errors**: Malformed request/response data
- **Tool Errors**: Invalid parameters or tool-specific failures

### Testing Strategy

- **Unit Tests**: Individual tool functionality
- **Integration Tests**: End-to-end tool chains
- **Mock Testing**: Isolated component testing
- **Live Testing**: Full system validation with mock server

## Development

See [AGENTS.md](AGENTS.md) for development guidelines, coding standards, and build/test commands.

## Contributing

1. Follow the coding standards in AGENTS.md
2. Add tests for new functionality
3. Update documentation as needed
4. Run tests before submitting changes
5. Test with both mock and real Redfish servers</content>
<parameter name="filePath">/home/dev/workspace/mcp/test/README.md