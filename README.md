# Redfish MCP Project

An intelligent Redfish server management system using Model Context Protocol (MCP) and AI-powered chatbots.

## Overview

This project provides an AI-powered interface for managing Redfish-enabled servers through natural language commands. Redfish routes, writable fields, and actions differ by target, so the server learns them with read-only requests and stores a typed contract. The model sees a small, fixed tool list. The server builds every PATCH and POST from that contract.

- **Chatbot Interface**: Interactive AI assistant for Redfish operations
- **MCP Server**: Stateless Model Context Protocol server with a fixed tool surface
- **Capability service**: Resolves resources and builds writes without exposing stored contracts
- **Mock Server**: Local Redfish target used to exercise discovery and writes

## Quick Start

1. **Set up Redfish Mock Server** (see [User Guide](#user-guide) for details)
2. **Install dependencies** and set API key
3. **Start MCP Server** and **run Chatbot**

## Project Structure

```
├── src/
│   └── redfish_mcp/
│       ├── redfish_mcp_server.py   # Fixed FastMCP tool surface
│       ├── redfish_tool.py         # Same tools for the LangChain chatbot
│       ├── capability_service.py   # Adapter-facing service
│       ├── contract.py             # Read-only exploration and write builder
│       ├── store.py                # Shared SQLite or Redis contract store
│       ├── client.py               # Guarded Redfish HTTP client
│       ├── config.py               # Environment configuration
│       └── chatbot.py              # Natural-language client
├── tests/                          # Contract, store, client, and chatbot tests
├── docs/                           # Published Redfish specification references
├── scripts/
│   └── mock_redfish_server.py      # Mock target with ETag, Settings, and actions
├── AGENTS.md
└── README.md
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

You: Turn on the indicator LED for the wireless interface

Bot: The wireless interface is identified by context, so I will set only that resource.

[Tool Call: set_properties]
{"status": "updated", "http_status": 204, "contract_revision": 3, "audit_id": "..."}

You: Change IPAddress to 192.0.2.2

Bot: More than one resource publishes IPAddress, and the request does not identify one.

[Tool Call: set_properties]
{"status": "ambiguous_target", "candidates": [
  {"candidate_id": "...", "label": "Ethernet Adapter", "interface_kind": "ethernet"},
  {"candidate_id": "...", "label": "Wireless Adapter", "interface_kind": "wireless"}
]}

Bot: Which interface should be changed?

You: quit
```

The server does not write when a selector matches zero resources or more than one. It returns `not_found` or `ambiguous_target`. The model uses conversation context to refine the selector and asks the person to choose a `candidate_id` only when that context is not enough.

### Testing the Tools Directly

You can also test individual tools without the AI interface:

```bash
# List service-root links
PYTHONPATH=. python3 -c "from src.redfish_mcp.redfish_tool import list_endpoints; print(list_endpoints.invoke({}))"

# Read one resource
PYTHONPATH=. python3 -c "from src.redfish_mcp.redfish_tool import get_endpoint_data; print(get_endpoint_data.invoke({'endpoint_url': '/Systems'}))"

# Find every resource that publishes a writable property
PYTHONPATH=. python3 -c "from src.redfish_mcp.redfish_tool import find_capabilities; print(find_capabilities.invoke({'query': 'IndicatorLED'}))"
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

MCP sessions stay stateless. The FastMCP and LangChain adapters call `CapabilityService` and never see the store, a cache hit, or a refresh. `ContractResolver` decides whether to reuse, extend, invalidate, or rebuild the learned contract.

```
MCP client or chatbot
        |
        v
Fixed tools: list_endpoints, get_endpoint_data,
             find_capabilities, set_properties, invoke_action
        |
        v
CapabilityService
        |
        v
ContractResolver ---- shared contract store (SQLite, or Redis when REDIS_URL is set)
        |
        v
RedfishClient ---- one Redfish service
```

### Fixed tool surface

| Tool | What the caller supplies | What the server does |
| --- | --- | --- |
| `list_endpoints()` | Nothing | Reads the service root and lists its links |
| `get_endpoint_data(endpoint_url)` | A resource path | Returns that resource's operational JSON |
| `find_capabilities(query, selector={})` | A property or action name, plus optional context | Returns compact matches and candidate labels |
| `set_properties(updates, selector={}, candidate_id=None)` | Values keyed by slash paths such as `IndicatorLED` or `Boot/BootSourceOverrideEnabled` | Builds and sends one PATCH |
| `invoke_action(action_name, arguments={}, selector={}, candidate_id=None)` | Action name and argument values | Builds and sends one POST |

`patch_resource` and `post_action` are not exposed. Callers cannot submit a raw PATCH document, an action URL, or an HTTP header. A GET body is not reused as a PATCH: `@odata.*`, `Status`, links, and every property outside the learned allowlist stay out of the request.

### How a write is resolved

1. The caller supplies selectors already known from context: `endpoint`, `resource_type`, `Id`, `Name`, `interface_kind`, or `ancestor_path`. Every selector matches the whole value, so `Id` `1` does not select resource `10`. The server never picks the first match.
2. One match proceeds. Zero matches return `not_found` and do not write. Several matches return `ambiguous_target` with labels and opaque `candidate_id` values and do not write.
3. The model refines the selector when the conversation already identifies the resource. It asks the person to choose only as a last resort, then retries with that `candidate_id`.
4. A candidate is bound to the service, role, contract revision, operation, and a short expiry (`CANDIDATE_TTL_SECONDS`, default 300). A stale or cross-role ID cannot authorize a later write.

### Learned contract

`src/redfish_mcp/contract.py` keeps one versioned document per service UUID and Redfish role. Its revision increases monotonically, including after the document is invalidated.

The resolver explores with GET requests only. Starting at the service root, it follows same-origin `@odata.id` navigation properties, collection members, and `Members@odata.nextLink` pages. It canonicalizes each URI, visits it once, and records the link path used to reach it. It does not follow an edge back to the current resource or its immediate parent. A URI fragment is a JSON Pointer into the fetched resource, not a separate writable URI. `Actions` and `@Redfish.Settings` are classified instead of being crawled as ordinary resources.

Exploration is breadth-first and bounded by `EXPLORE_MAX_RESOURCES` (default 200) and `EXPLORE_MAX_DEPTH` (default 8). Unfinished work remains in the stored frontier. A budget or failed-link result is `budget_limited`; it is not treated as proof that a property is unsupported. Completed topology is refreshed after `CONTRACT_REFRESH_TTL_SECONDS` (default 300 seconds).

Each resource section records:

- `@odata.type` and the `Allow` header of the write target
- The PATCH URI, which is `SettingsObject.@odata.id` when `@Redfish.Settings` is present
- `SupportedApplyTimes` as a caller-supplied `@Redfish.SettingsApplyTime/ApplyTime` value; the server does not choose one
- Writable properties from the first published allowlist: `@Redfish.AllowableValues` or `@Redfish.WriteableProperties`, then JSON Schema properties explicitly marked writable, then the same sources on the Settings object. A Settings leaf is not assumed writable merely because it appears in the Settings document. If no source publishes an allowlist, writes to that resource are refused.
- Actions from the `Actions` object. Parameter names, types, required flags, and allowable values come only from ActionInfo. Absent ActionInfo accepts an empty body and rejects named arguments. A failed or budget-limited ActionInfo lookup rejects the action.

Before use, the resolver compares the stored generation with a live probe: service `UUID`, `RedfishVersion`, each Manager `FirmwareVersion`, and a fingerprint of observed `@odata.type` values plus JSON Schema ETags that were actually fetched. A generation change, an incompatible contract format, or an expired topology deletes that role's contract and explores again. Audit rows remain.

Immediately before PATCH or POST, the server GETs the write target again. It sends `If-Match` from that response's `ETag` header or `@odata.etag`. A missing fresh ETag or a changed `@odata.type` stops the write. The precondition is not stored in the contract. The response includes `contract_revision` and `audit_id`. The audit record contains the timestamp, service UUID, role, revision, operation, URI, SHA-256 of the built body, and HTTP status.

### Identity and isolation

`REDFISH_USERNAME` and `REDFISH_PASSWORD` are sent as HTTP basic authentication. The role comes from `AccountService/Accounts` by matching `UserName` to `RoleId`. Accounts with the same role share one contract because they receive the same Redfish permissions. If the account list cannot be read, the key is `user:{username}` so that caller is not placed in another role's contract. No credentials use the `anonymous` role.

### Shared store

`src/redfish_mcp/store.py` implements get, compare-and-swap put, invalidate, and append-only audit.

- The default is a SQLite file at `CONTRACT_SQLITE_PATH`, using WAL mode and `BEGIN IMMEDIATE` around each revision update. Processes on one host can share the file.
- `REDIS_URL` selects Redis. The revision update runs in one Lua script so two instances cannot overwrite each other. Startup fails with a configuration error when that URL is set and Redis cannot be imported or reached.

There is no public refresh or cache tool. A short process-local probe cache (`CONTRACT_PROBE_TTL_SECONDS`, default 30) is only a hint and is always compared with the stored generation.

### Target protection

`RedfishClient` rejects an absolute URL or redirect whose origin differs from `REDFISH_BASE_URL`. It accepts absolute Redfish paths such as `/redfish/v1/Systems` without duplicating the service prefix. Responses larger than `MAX_RESPONSE_BYTES` (default 1 MiB) are rejected. Each resource exploration reads at most one Settings object, `EXPLORE_MAX_ACTIONS` ActionInfo documents (default 16), and one schema document. Only a structurally valid section is stored. GET, and idempotent PATCH, keep retry and circuit-breaker protection. Action POST requests are not retried.

### Components

1. **MCP server** (`src/redfish_mcp/redfish_mcp_server.py`): registers the five fixed FastMCP tools and validates configuration without requiring an Anthropic key.
2. **LangChain tools** (`src/redfish_mcp/redfish_tool.py`): exposes those same operations to the chatbot.
3. **Capability service** (`src/redfish_mcp/capability_service.py`): constructs the client, store, and resolver from configuration. Tool results are JSON strings with no store or cache metadata.
4. **Contract resolver** (`src/redfish_mcp/contract.py`): owns exploration, selection, PATCH and action construction, preconditions, invalidation, and audit.
5. **Contract store** (`src/redfish_mcp/store.py`): shares revisioned contracts and preserves write history across instances.
6. **Redfish client** (`src/redfish_mcp/client.py`): applies authentication, origin checks, response limits, retries, and the circuit breaker.
7. **Chatbot** (`src/redfish_mcp/chatbot.py`): asks the model to use contextual selectors first, refine an ambiguous result second, and ask the user only as a last resort.
8. **Mock server** (`scripts/mock_redfish_server.py`): publishes firmware identity, `ETag`, `Allow`, allowable `IndicatorLED` values, a separate Settings URI, and `ComputerSystem.Reset` with ActionInfo.

### Data flow

1. The caller asks for a property change or action and includes any target identity already present in the conversation.
2. The resolver probes service identity and role, then loads or rebuilds that role's contract.
3. It continues the stored read-only traversal until the requested capability is indexed or a budget is reached.
4. One exact candidate is required. Otherwise the call returns without sending a write.
5. The server validates values against the contract, fetches a fresh ETag, and sends the constructed PATCH or POST.
6. The store appends an audit row naming the contract revision, and the tool returns that revision with the audit ID.

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

- **Network and transport**: connection failures, timeouts, retries, and an open circuit breaker
- **Target safety**: off-origin URLs and redirects, oversized responses, and missing fresh ETags
- **Contract results**: `not_found`, `ambiguous_target`, `ambiguous_action`, `budget_limited`, `stale_candidate`, `contract_changed`, and `rejected`
- **Redfish responses**: authentication failures and other HTTP status codes, recorded in the audit row when a built write was attempted

### Testing Strategy

- **Contract tests**: minimal PATCH bodies, Settings URIs, fresh `If-Match`, exact selectors, ambiguity, candidate expiry, role isolation, firmware invalidation, pagination, cycles, and ActionInfo validation
- **Store tests**: SQLite compare-and-swap and monotonic revisions; Redis behavior through a fake client, with a live Redis test skipped unless `REDIS_URL` is set
- **Client tests**: same-origin URL handling, redirect rejection, and response-size limits
- **Chatbot test**: dispatch through the fixed tool map without a live model or Redfish target
- **Mock server**: local target that publishes the annotations required to learn a write contract

## Development

See [AGENTS.md](AGENTS.md) for development guidelines, coding standards, and build/test commands.

## Contributing

1. Follow the coding standards in AGENTS.md
2. Add tests for new functionality
3. Update documentation as needed
4. Run tests before submitting changes
5. Test with both mock and real Redfish servers</content>
<parameter name="filePath">/home/dev/workspace/mcp/test/README.md