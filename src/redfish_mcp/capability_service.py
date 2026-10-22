"""Application service exposed by MCP and other tool adapters."""

import json
from typing import Any, Dict, Optional

from .circuit_breaker import CircuitBreaker
from .client import RedfishClient
from .config import config
from .contract import ContractResolver
from .exceptions import (
    RedfishConnectionError,
    RedfishServerError,
    RedfishTimeoutError,
)
from .retry import RetryConfig
from .store import create_contract_store


class CapabilityService:
    """Small facade that keeps contract storage invisible to MCP tools."""

    def __init__(self, resolver: ContractResolver):
        """Initialize the service with a resolver."""
        self.resolver = resolver

    def list_endpoints(self) -> str:
        """List service-root endpoints."""
        return self.resolver.client.list_endpoints()

    def get_endpoint_data(self, endpoint_url: str) -> str:
        """Read a Redfish resource."""
        return self.resolver.client.get_endpoint_data(endpoint_url)

    def find_capabilities(
        self, query: str, selector: Optional[Dict[str, str]] = None
    ) -> str:
        """Return matching resources, properties, and actions."""
        return json.dumps(
            self.resolver.find_capabilities(query, selector),
            sort_keys=True,
        )

    def set_properties(
        self,
        updates: Dict[str, Any],
        selector: Optional[Dict[str, str]] = None,
        candidate_id: Optional[str] = None,
    ) -> str:
        """Safely set properties on one resolved Redfish resource."""
        return json.dumps(
            self.resolver.set_properties(updates, selector, candidate_id),
            sort_keys=True,
        )

    def invoke_action(
        self,
        action_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        selector: Optional[Dict[str, str]] = None,
        candidate_id: Optional[str] = None,
    ) -> str:
        """Safely invoke an action on one resolved Redfish resource."""
        return json.dumps(
            self.resolver.invoke_action(
                action_name, arguments, selector, candidate_id
            ),
            sort_keys=True,
        )


def create_capability_service() -> CapabilityService:
    """Build the configured capability service."""
    retry_config = RetryConfig(
        max_attempts=config.MAX_RETRY_ATTEMPTS,
        base_delay=config.RETRY_BASE_DELAY,
        max_delay=config.RETRY_MAX_DELAY,
        retry_on=(
            RedfishConnectionError,
            RedfishTimeoutError,
            RedfishServerError,
        ),
    )
    circuit_breaker = (
        CircuitBreaker(
            failure_threshold=config.CIRCUIT_BREAKER_THRESHOLD,
            recovery_timeout=config.CIRCUIT_BREAKER_TIMEOUT,
            expected_exception=(
                RedfishConnectionError,
                RedfishTimeoutError,
                RedfishServerError,
            ),
        )
        if config.ENABLE_CIRCUIT_BREAKER
        else None
    )
    client = RedfishClient(
        base_url=config.REDFISH_BASE_URL,
        timeout=config.REQUEST_TIMEOUT,
        verify_ssl=config.VERIFY_SSL,
        enable_retry=config.ENABLE_RETRY,
        enable_circuit_breaker=config.ENABLE_CIRCUIT_BREAKER,
        retry_config=retry_config,
        circuit_breaker=circuit_breaker,
        username=config.REDFISH_USERNAME,
        password=config.REDFISH_PASSWORD,
        max_response_bytes=config.MAX_RESPONSE_BYTES,
    )
    store = create_contract_store(
        config.CONTRACT_SQLITE_PATH,
        config.REDIS_URL,
    )
    resolver = ContractResolver(
        client,
        store,
        username=config.REDFISH_USERNAME,
        probe_ttl_seconds=config.CONTRACT_PROBE_TTL_SECONDS,
        topology_ttl_seconds=config.CONTRACT_REFRESH_TTL_SECONDS,
        candidate_ttl_seconds=config.CANDIDATE_TTL_SECONDS,
        max_resources=config.EXPLORE_MAX_RESOURCES,
        max_depth=config.EXPLORE_MAX_DEPTH,
        max_actions=config.EXPLORE_MAX_ACTIONS,
    )
    return CapabilityService(resolver)
