"""Read-only Redfish exploration and contract-backed write construction."""

import base64
import hashlib
import json
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple
from urllib.parse import urldefrag, urlparse

from .client import RedfishClient
from .exceptions import RedfishError
from .store import ContractConflictError, ContractStore


CONTRACT_FORMAT_VERSION = 1
READ_ONLY_PROPERTIES = {
    "@odata.context",
    "@odata.etag",
    "@odata.id",
    "@odata.type",
    "Actions",
    "Description",
    "Id",
    "Links",
    "Name",
    "Oem",
    "Status",
}


@dataclass(frozen=True)
class TargetContext:
    """Identity and generation for the current Redfish view."""

    key: str
    service_uuid: str
    role: str
    generation: Dict[str, Any]
    root: Dict[str, Any]


class ContractResolver:
    """Resolve capabilities while hiding persistence and exploration mechanics."""

    def __init__(
        self,
        client: RedfishClient,
        store: ContractStore,
        username: Optional[str] = None,
        probe_ttl_seconds: int = 30,
        topology_ttl_seconds: int = 300,
        candidate_ttl_seconds: int = 300,
        max_resources: int = 200,
        max_depth: int = 8,
        max_actions: int = 16,
    ):
        """Create a resolver with bounded exploration."""
        self.client = client
        self.store = store
        self.username = username
        self.probe_ttl_seconds = probe_ttl_seconds
        self.topology_ttl_seconds = topology_ttl_seconds
        self.candidate_ttl_seconds = candidate_ttl_seconds
        self.max_resources = max_resources
        self.max_depth = max_depth
        self.max_actions = max_actions
        self._cached_context: Optional[TargetContext] = None
        self._probe_time = 0.0
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._schema_etags: Set[str] = set()

    def find_capabilities(
        self, query: str, selector: Optional[Mapping[str, str]] = None
    ) -> Dict[str, Any]:
        """Find writable properties and actions matching a compact query."""
        context, contract = self._load_contract()
        contract, complete = self._explore(context, contract)
        query_lower = query.lower().strip()
        resources = self._select_resources(contract, selector or {})
        matches: List[Dict[str, Any]] = []
        for resource in resources:
            properties = {
                path: definition
                for path, definition in resource["writable"].items()
                if query_lower in path.lower()
            }
            actions = {
                name: definition
                for name, definition in resource["actions"].items()
                if query_lower in name.lower()
            }
            if properties or actions:
                matches.append(
                    self._public_candidate(
                        context, contract, resource, "find", properties, actions
                    )
                )
        return {
            "status": "ok" if matches else ("not_found" if complete else "budget_limited"),
            "query": query,
            "candidates": matches,
            "exploration_complete": complete,
        }

    def set_properties(
        self,
        updates: Mapping[str, Any],
        selector: Optional[Mapping[str, str]] = None,
        candidate_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve one resource, build a minimal PATCH, and execute it."""
        if not updates:
            return {"status": "invalid_request", "message": "updates cannot be empty"}
        context, contract = self._load_contract(force_probe=True)
        contract, complete = self._explore(context, contract)
        candidates = [
            item
            for item in self._select_resources(contract, selector or {})
            if set(updates).issubset(item["writable"])
            and (not item["allow"] or "PATCH" in item["allow"])
        ]
        chosen = self._resolve_candidate(
            context, contract, candidates, "set_properties", candidate_id, complete
        )
        if isinstance(chosen, dict) and "status" in chosen:
            return chosen
        resource = chosen
        try:
            body = self._build_patch(resource, updates)
            return self._execute_patch(context, contract, resource, body)
        except (TypeError, ValueError, RedfishError) as exc:
            return {"status": "rejected", "message": str(exc)}

    def invoke_action(
        self,
        action_name: str,
        arguments: Optional[Mapping[str, Any]] = None,
        selector: Optional[Mapping[str, str]] = None,
        candidate_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve one action, validate arguments, and execute it."""
        context, contract = self._load_contract(force_probe=True)
        contract, complete = self._explore(context, contract)
        candidates = [
            item
            for item in self._select_resources(contract, selector or {})
            if self._action_keys(item, action_name)
        ]
        chosen = self._resolve_candidate(
            context, contract, candidates, f"action:{action_name}", candidate_id, complete
        )
        if isinstance(chosen, dict) and "status" in chosen:
            return chosen
        resource = chosen
        matching_actions = self._action_keys(resource, action_name)
        if len(matching_actions) != 1:
            return {
                "status": "ambiguous_action",
                "message": "Use the full action name",
                "actions": matching_actions,
            }
        key = matching_actions[0]
        try:
            body = self._build_action(resource["actions"][key], arguments or {})
            return self._execute_action(
                context, contract, resource, key, body
            )
        except (TypeError, ValueError, RedfishError) as exc:
            return {"status": "rejected", "message": str(exc)}

    def _probe(self, force: bool = False) -> TargetContext:
        now = time.monotonic()
        if (
            not force
            and self._cached_context
            and now - self._probe_time < self.probe_ttl_seconds
        ):
            return self._cached_context
        root = self.client.get("")
        service_uuid = str(
            root.get("UUID")
            or hashlib.sha256(self.client.base_url.encode()).hexdigest()[:24]
        )
        role = self._resolve_role(root)
        generation = {
            "service_uuid": service_uuid,
            "redfish_version": root.get("RedfishVersion"),
            "firmware": self._manager_firmware(root),
        }
        key = f"{service_uuid}:{role}"
        context = TargetContext(key, service_uuid, role, generation, root)
        self._cached_context = context
        self._probe_time = now
        return context

    def _resolve_role(self, root: Mapping[str, Any]) -> str:
        if not self.username:
            return "anonymous"
        try:
            account_service = root.get("AccountService", {}).get("@odata.id")
            if not account_service:
                return f"user:{self.username}"
            service = self.client.get(account_service)
            accounts_uri = service.get("Accounts", {}).get("@odata.id")
            collection = self.client.get(accounts_uri)
            for member in collection.get("Members", []):
                account = self.client.get(member["@odata.id"])
                if account.get("UserName") == self.username:
                    return f"role:{account.get('RoleId', self.username)}"
        except (KeyError, TypeError, RedfishError):
            pass
        return f"user:{self.username}"

    def _manager_firmware(self, root: Mapping[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        try:
            managers_uri = root.get("Managers", {}).get("@odata.id")
            if not managers_uri:
                return result
            collection = self.client.get(managers_uri)
            for member in collection.get("Members", [])[:16]:
                manager = self.client.get(member["@odata.id"])
                result[str(manager.get("Id", member["@odata.id"]))] = manager.get(
                    "FirmwareVersion"
                )
        except (KeyError, TypeError, RedfishError):
            return result
        return result

    def _load_contract(
        self, force_probe: bool = False
    ) -> Tuple[TargetContext, Dict[str, Any]]:
        context = self._probe(force_probe)
        contract = self.store.get(context.key)
        incompatible = contract and contract.get("format_version") != CONTRACT_FORMAT_VERSION
        stale_topology = (
            contract
            and not contract.get("frontier")
            and time.time() - float(contract.get("explored_at", 0))
            >= self.topology_ttl_seconds
        )
        if contract and (
            incompatible
            or stale_topology
            or contract.get("generation") != context.generation
        ):
            self._invalidate(context.key)
            contract = None
        if contract is None:
            root_uri = str(context.root.get("@odata.id") or self.client.base_url)
            contract = {
                "format_version": CONTRACT_FORMAT_VERSION,
                "revision": 0,
                "target": context.service_uuid,
                "role": context.role,
                "generation": context.generation,
                "resources": {},
                "visited": [],
                "frontier": [
                    {
                        "uri": root_uri,
                        "parent": None,
                        "depth": 0,
                        "link_path": "ServiceRoot",
                    }
                ],
            }
        return context, contract

    def _explore(
        self, context: TargetContext, contract: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        explored = 0
        visited: Set[str] = set(contract.get("visited", []))
        frontier = list(contract.get("frontier", []))
        resources = contract.setdefault("resources", {})
        exploration_errors = contract.setdefault("exploration_errors", [])
        incomplete = contract.setdefault("incomplete", [])
        if not frontier:
            return contract, not incomplete
        while frontier and explored < self.max_resources:
            item = frontier.pop(0)
            uri, fragment = urldefrag(str(item["uri"]))
            canonical = self._canonical(uri)
            if canonical in visited:
                continue
            if item["depth"] > self.max_depth:
                incomplete.append({"uri": uri, "reason": "depth_limit"})
                continue
            try:
                payload, headers, _ = self.client.get_with_headers(uri)
                if not isinstance(payload, dict):
                    raise TypeError("resource payload is not an object")
            except (KeyError, TypeError, ValueError, RedfishError) as exc:
                if item["depth"] == 0:
                    raise
                exploration_errors.append({"uri": uri, "error": str(exc)})
                explored += 1
                attempts = int(item.get("attempts", 0)) + 1
                if attempts < 3:
                    retry_item = dict(item)
                    retry_item["attempts"] = attempts
                    frontier.append(retry_item)
                else:
                    incomplete.append({"uri": uri, "reason": "request_failed"})
                continue
            visited.add(canonical)
            explored += 1
            section = self._resource_section(payload, headers, item, fragment)
            resources[canonical] = section
            frontier.extend(
                self._linked_resources(payload, uri, item, visited)
            )
        contract["visited"] = sorted(visited)
        contract["frontier"] = frontier
        contract["schema_fingerprint"] = self._schema_fingerprint(
            resources.values(), self._schema_etags
        )
        if not frontier:
            contract["explored_at"] = time.time()
        contract = self._persist(context.key, contract)
        return contract, not contract.get("frontier") and not contract.get("incomplete")

    def _resource_section(
        self,
        payload: Dict[str, Any],
        headers: Mapping[str, str],
        item: Mapping[str, Any],
        fragment: str,
    ) -> Dict[str, Any]:
        resource_uri = str(payload.get("@odata.id") or item["uri"]).split("#", 1)[0]
        write_uri = resource_uri
        allow = self._header(headers, "Allow")
        writable = self._annotated_writable(payload)
        if not writable and payload.get("@odata.type"):
            writable = self._schema_writable(str(payload["@odata.type"]))
        settings = payload.get("@Redfish.Settings")
        write_type = payload.get("@odata.type")
        if isinstance(settings, dict):
            settings_uri = settings.get("SettingsObject", {}).get("@odata.id")
            if settings_uri:
                try:
                    settings_payload, settings_headers, _ = self.client.get_with_headers(
                        settings_uri
                    )
                    write_uri = settings_uri
                    write_type = settings_payload.get("@odata.type")
                    writable.update(self._settings_writable(settings_payload))
                    allow = self._header(settings_headers, "Allow") or allow
                except RedfishError:
                    pass
            apply_times = settings.get("SupportedApplyTimes")
            if apply_times:
                writable["@Redfish.SettingsApplyTime/ApplyTime"] = {
                    "type": "string",
                    "allowable_values": list(apply_times),
                }
        actions = self._actions(payload)
        return {
            "uri": resource_uri,
            "odata_type": payload.get("@odata.type"),
            "write_uri": write_uri,
            "write_odata_type": write_type,
            "allow": [value.strip().upper() for value in allow.split(",") if value.strip()],
            "id": payload.get("Id"),
            "name": payload.get("Name"),
            "parent": item.get("parent"),
            "link_path": item.get("link_path"),
            "depth": item.get("depth", 0),
            "fragment": fragment or None,
            "interface_kind": self._interface_kind(payload, item),
            "writable": writable,
            "actions": actions,
            "fragment_references": self._fragment_references(payload, resource_uri),
        }

    def _annotated_writable(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        explicit = payload.get("@Redfish.WriteableProperties", [])
        for path in explicit if isinstance(explicit, list) else []:
            result[str(path)] = {"type": "unknown", "allowable_values": None}
        for key, values in payload.items():
            suffix = "@Redfish.AllowableValues"
            if not key.endswith(suffix) or not isinstance(values, list):
                continue
            property_name = key[: -len(suffix)]
            result[property_name] = {
                "type": self._value_type(payload.get(property_name)),
                "allowable_values": values,
            }
        return result

    def _schema_writable(self, odata_type: str) -> Dict[str, Any]:
        if odata_type in self._schema_cache:
            return deepcopy(self._schema_cache[odata_type])
        self._schema_cache[odata_type] = {}
        root = self._cached_context.root if self._cached_context else {}
        collection_uri = root.get("JsonSchemas", {}).get("@odata.id")
        if not collection_uri:
            return {}
        resource_name = odata_type.strip("#").split(".", 1)[0]
        try:
            collection = self.client.get(collection_uri)
            for member in collection.get("Members", [])[: self.max_resources]:
                descriptor = self.client.get(member["@odata.id"])
                schema_name = str(
                    descriptor.get("Schema")
                    or descriptor.get("Name")
                    or descriptor.get("Id")
                    or ""
                )
                if schema_name.lower() != resource_name.lower():
                    continue
                for location in descriptor.get("Location", []):
                    uri = location.get("Uri")
                    if not uri:
                        continue
                    schema, headers, _ = self.client.get_with_headers(uri)
                    etag = self._header(headers, "ETag") or schema.get("@odata.etag")
                    if etag:
                        self._schema_etags.add(str(etag))
                    writable = self._writable_from_json_schema(
                        schema, resource_name
                    )
                    if writable:
                        self._schema_cache[odata_type] = deepcopy(writable)
                        return deepcopy(writable)
        except (KeyError, TypeError, RedfishError):
            return {}
        return {}

    def _writable_from_json_schema(
        self, schema: Mapping[str, Any], resource_name: str
    ) -> Dict[str, Any]:
        definitions = schema.get("definitions", {})
        candidates = [
            value
            for key, value in definitions.items()
            if resource_name.lower() in key.lower()
            and isinstance(value, dict)
            and isinstance(value.get("properties"), dict)
        ]
        if not candidates and isinstance(schema.get("properties"), dict):
            candidates = [schema]
        if not candidates:
            return {}
        properties = candidates[-1]["properties"]
        result: Dict[str, Any] = {}
        for name, definition in properties.items():
            if name in READ_ONLY_PROPERTIES or name.startswith("@"):
                continue
            if not isinstance(definition, dict):
                continue
            if definition.get("readonly") is not False and not definition.get(
                "writeOnly", False
            ):
                continue
            if "$ref" in definition:
                continue
            schema_type = definition.get("type", "unknown")
            if isinstance(schema_type, list):
                non_null_types = [
                    item for item in schema_type if str(item).lower() != "null"
                ]
                if len(non_null_types) != 1:
                    continue
                schema_type = non_null_types[0]
            result[name] = {
                "type": str(schema_type).lower(),
                "allowable_values": definition.get("enum"),
            }
        return result

    def _settings_writable(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        result = self._annotated_writable(payload)
        odata_type = payload.get("@odata.type")
        if not result and odata_type:
            result.update(self._schema_writable(str(odata_type)))
        return result

    def _actions(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        action_count = 0
        for raw_name, value in payload.get("Actions", {}).items():
            if not isinstance(value, dict) or "target" not in value:
                continue
            name = raw_name.lstrip("#")
            definition = {
                "target": value["target"],
                "parameters": {},
                "action_info_status": "absent",
            }
            info_uri = value.get("@Redfish.ActionInfo")
            if info_uri and action_count >= self.max_actions:
                definition["action_info_status"] = "budget_limited"
            elif info_uri:
                try:
                    info = self.client.get(info_uri)
                    action_count += 1
                    definition["action_info_status"] = "loaded"
                    for parameter in info.get("Parameters", []):
                        definition["parameters"][parameter["Name"]] = {
                            "required": bool(parameter.get("Required", False)),
                            "type": str(parameter.get("DataType", "unknown")).lower(),
                            "allowable_values": parameter.get("AllowableValues"),
                        }
                except RedfishError:
                    definition["action_info_status"] = "failed"
            result[name] = definition
        return result

    def _linked_resources(
        self,
        payload: Mapping[str, Any],
        current_uri: str,
        item: Mapping[str, Any],
        visited: Set[str],
    ) -> List[Dict[str, Any]]:
        links: List[Dict[str, Any]] = []
        current = self._canonical(current_uri)
        parent = self._canonical(item["parent"]) if item.get("parent") else None
        for path, uri in self._odata_links(payload):
            base_uri, _ = urldefrag(uri)
            try:
                self.client._build_url(base_uri)
            except RedfishError:
                continue
            canonical = self._canonical(base_uri)
            if canonical in {current, parent} or canonical in visited:
                continue
            links.append(
                {
                    "uri": uri,
                    "parent": current_uri,
                    "depth": int(item.get("depth", 0)) + 1,
                    "link_path": f"{item.get('link_path', '')}/{path}".strip("/"),
                }
            )
        return links

    def _odata_links(
        self, value: Any, path: str = ""
    ) -> Iterable[Tuple[str, str]]:
        if isinstance(value, dict):
            if isinstance(value.get("@odata.id"), str):
                yield path or "@odata.id", value["@odata.id"]
            for key, child in value.items():
                if key in ("Actions", "@Redfish.Settings") or key == "@odata.id":
                    continue
                child_path = f"{path}/{key}" if path else key
                if key in ("Members@odata.nextLink", "@odata.nextLink") and isinstance(
                    child, str
                ):
                    yield child_path, child
                    continue
                yield from self._odata_links(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from self._odata_links(child, f"{path}/{index}")

    def _fragment_references(
        self, payload: Mapping[str, Any], resource_uri: str
    ) -> List[Dict[str, Any]]:
        references: List[Dict[str, Any]] = []
        canonical = self._canonical(resource_uri)
        for path, uri in self._odata_links(payload):
            base_uri, fragment = urldefrag(uri)
            if fragment and self._canonical(base_uri) == canonical:
                references.append(
                    {
                        "link_path": path,
                        "fragment": fragment,
                        "value_type": self._value_type(
                            self._json_pointer(payload, fragment)
                        ),
                    }
                )
        return references

    @staticmethod
    def _json_pointer(payload: Mapping[str, Any], fragment: str) -> Any:
        current: Any = payload
        for raw_part in fragment.lstrip("/").split("/"):
            if not raw_part:
                continue
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if isinstance(current, list):
                current = current[int(part)]
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _select_resources(
        self, contract: Mapping[str, Any], selector: Mapping[str, str]
    ) -> List[Dict[str, Any]]:
        resources = list(contract.get("resources", {}).values())
        if not selector:
            return resources
        aliases = {
            "endpoint": "uri",
            "resource_type": "odata_type",
            "Id": "id",
            "Name": "name",
            "ancestor_path": "link_path",
        }
        selected = []
        for resource in resources:
            matches = True
            for raw_key, expected in selector.items():
                key = aliases.get(raw_key, raw_key)
                actual = resource.get(key)
                if key == "link_path":
                    matches_value = (
                        actual is not None
                        and str(expected).casefold() == str(actual).casefold()
                    )
                elif key == "uri":
                    matches_value = (
                        actual is not None
                        and self._canonical(str(expected))
                        == self._canonical(str(actual))
                    )
                else:
                    matches_value = (
                        actual is not None
                        and str(expected).casefold() == str(actual).casefold()
                    )
                if not matches_value:
                    matches = False
                    break
            if matches:
                selected.append(resource)
        return selected

    def _resolve_candidate(
        self,
        context: TargetContext,
        contract: Mapping[str, Any],
        candidates: List[Dict[str, Any]],
        operation: str,
        candidate_id: Optional[str],
        complete: bool,
    ) -> Any:
        if candidate_id:
            selected = [
                item
                for item in candidates
                if candidate_id
                in self._valid_candidate_ids(context, contract, operation, item)
            ]
            if len(selected) == 1:
                return selected[0]
            return {"status": "stale_candidate", "message": "Candidate is invalid or stale"}
        if len(candidates) == 1 and complete:
            return candidates[0]
        if not complete:
            return {
                "status": "budget_limited",
                "message": "Exploration is incomplete; retry to continue safely",
            }
        if not candidates:
            return {"status": "not_found", "message": "No matching writable resource"}
        return {
            "status": "ambiguous_target",
            "message": "Refine the selector; ask the user only if context cannot decide",
            "candidates": [
                self._public_candidate(
                    context, contract, item, operation, item["writable"], item["actions"]
                )
                for item in candidates
            ],
        }

    def _public_candidate(
        self,
        context: TargetContext,
        contract: Mapping[str, Any],
        resource: Mapping[str, Any],
        operation: str,
        properties: Mapping[str, Any],
        actions: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return {
            "candidate_id": self._candidate_id(context, contract, operation, resource),
            "label": resource.get("name") or resource.get("id") or resource["uri"],
            "uri": resource["uri"],
            "resource_type": resource.get("odata_type"),
            "id": resource.get("id"),
            "name": resource.get("name"),
            "path": resource.get("link_path"),
            "interface_kind": resource.get("interface_kind"),
            "writable_properties": properties,
            "actions": actions,
        }

    def _candidate_id(
        self,
        context: TargetContext,
        contract: Mapping[str, Any],
        operation: str,
        resource: Mapping[str, Any],
        bucket: Optional[int] = None,
    ) -> str:
        if bucket is None:
            bucket = int(time.time() // self.candidate_ttl_seconds)
        payload = "|".join(
            [
                context.key,
                str(contract.get("revision", 0)),
                operation,
                str(resource["uri"]),
                str(bucket),
            ]
        )
        digest = hashlib.sha256(payload.encode()).digest()[:18]
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def _valid_candidate_ids(
        self,
        context: TargetContext,
        contract: Mapping[str, Any],
        operation: str,
        resource: Mapping[str, Any],
    ) -> Set[str]:
        bucket = int(time.time() // self.candidate_ttl_seconds)
        current = self._candidate_id(
            context, contract, operation, resource, bucket
        )
        previous = self._candidate_id(
            context, contract, operation, resource, bucket - 1
        )
        return {current, previous}

    def _build_patch(
        self, resource: Mapping[str, Any], updates: Mapping[str, Any]
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        for path, value in updates.items():
            definition = resource["writable"].get(path)
            if definition is None:
                allowed = ", ".join(sorted(resource["writable"]))
                raise ValueError(f"Property '{path}' is not writable. Allowed: {allowed}")
            self._validate_value(path, value, definition)
            cursor = body
            parts = path.split("/")
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[parts[-1]] = value
        return body

    def _build_action(
        self, action: Mapping[str, Any], arguments: Mapping[str, Any]
    ) -> Dict[str, Any]:
        parameters = action.get("parameters", {})
        action_info_status = action.get("action_info_status", "absent")
        if action_info_status in ("failed", "budget_limited"):
            raise ValueError(
                f"Action parameter contract is {action_info_status}; action refused"
            )
        if action_info_status == "absent" and arguments:
            raise ValueError("ActionInfo is absent; named arguments are not accepted")
        unknown = set(arguments) - set(parameters)
        if unknown:
            raise ValueError(f"Unknown action arguments: {', '.join(sorted(unknown))}")
        required = {
            key for key, value in parameters.items() if value.get("required")
        }
        missing = required - set(arguments)
        if missing:
            raise ValueError(f"Missing action arguments: {', '.join(sorted(missing))}")
        for key, value in arguments.items():
            self._validate_value(key, value, parameters[key])
        return dict(arguments)

    def _execute_patch(
        self,
        context: TargetContext,
        contract: Mapping[str, Any],
        resource: Mapping[str, Any],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        live, headers, _ = self.client.get_with_headers(resource["write_uri"])
        expected_type = resource.get("write_odata_type")
        if expected_type and live.get("@odata.type") != expected_type:
            self._invalidate(context.key)
            return {"status": "contract_changed", "message": "Resource type changed; retry"}
        request_headers = self._precondition_headers(live, headers)
        try:
            _, status = self.client.patch_with_status(
                resource["write_uri"], body, request_headers
            )
        except RedfishError as exc:
            self._audit(
                context,
                contract,
                "PATCH",
                resource["write_uri"],
                body,
                exc.status_code or 0,
            )
            raise
        audit_id = self._audit(
            context, contract, "PATCH", resource["write_uri"], body, status
        )
        return {
            "status": "updated",
            "http_status": status,
            "contract_revision": contract["revision"],
            "audit_id": audit_id,
        }

    def _execute_action(
        self,
        context: TargetContext,
        contract: Mapping[str, Any],
        resource: Mapping[str, Any],
        action_name: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        live, headers, _ = self.client.get_with_headers(resource["uri"])
        if live.get("@odata.type") != resource.get("odata_type"):
            self._invalidate(context.key)
            return {"status": "contract_changed", "message": "Resource type changed; retry"}
        action = resource["actions"][action_name]
        request_headers = self._precondition_headers(live, headers)
        try:
            _, status = self.client.post_with_status(
                action["target"], body, request_headers
            )
        except RedfishError as exc:
            self._audit(
                context,
                contract,
                "POST",
                action["target"],
                body,
                exc.status_code or 0,
            )
            raise
        audit_id = self._audit(
            context, contract, "POST", action["target"], body, status
        )
        return {
            "status": "invoked",
            "http_status": status,
            "contract_revision": contract["revision"],
            "audit_id": audit_id,
        }

    def _audit(
        self,
        context: TargetContext,
        contract: Mapping[str, Any],
        operation: str,
        uri: str,
        body: Mapping[str, Any],
        status: int,
    ) -> str:
        body_hash = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return self.store.append_audit(
            {
                "contract_key": context.key,
                "service_uuid": context.service_uuid,
                "role": context.role,
                "contract_revision": contract["revision"],
                "operation": operation,
                "uri": uri,
                "body_sha256": body_hash,
                "http_status": status,
            }
        )

    def _persist(self, key: str, contract: Dict[str, Any]) -> Dict[str, Any]:
        expected = int(contract.get("revision", 0))
        stored = deepcopy(contract)
        try:
            revision = self.store.put(key, stored, expected)
        except ContractConflictError:
            current = self.store.get(key)
            if current is None:
                raise
            return current
        stored["revision"] = revision
        return stored

    def _invalidate(self, key: str) -> None:
        self.store.invalidate(key)
        self._schema_cache.clear()
        self._schema_etags.clear()

    @staticmethod
    def _precondition_headers(
        payload: Mapping[str, Any], headers: Mapping[str, str]
    ) -> Dict[str, str]:
        etag = ContractResolver._header(headers, "ETag") or payload.get("@odata.etag")
        if not etag:
            raise ValueError("Target did not provide a fresh ETag; write refused")
        return {"If-Match": str(etag)}

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str:
        for key, value in headers.items():
            if key.lower() == name.lower():
                return str(value)
        return ""

    @staticmethod
    def _validate_value(
        name: str, value: Any, definition: Mapping[str, Any]
    ) -> None:
        allowable = definition.get("allowable_values")
        if allowable is not None and value not in allowable:
            raise ValueError(f"{name} must be one of {allowable}")
        expected = str(definition.get("type", "unknown")).lower()
        valid = {
            "string": isinstance(value, str),
            "boolean": isinstance(value, bool),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "array": isinstance(value, list),
            "object": isinstance(value, dict),
            "unknown": True,
            "null": value is None,
        }
        if expected in valid and not valid[expected]:
            raise TypeError(f"{name} must be {expected}")

    @staticmethod
    def _action_keys(resource: Mapping[str, Any], requested: str) -> List[str]:
        requested_lower = requested.lower()
        exact = [
            key
            for key in resource.get("actions", {})
            if key.lower() == requested_lower
        ]
        if exact:
            return exact
        return [
            key
            for key in resource.get("actions", {})
            if key.rsplit(".", 1)[-1].lower() == requested_lower
        ]

    def _canonical(self, uri: str) -> str:
        raw_uri = urldefrag(str(uri))[0]
        try:
            raw_uri = self.client._build_url(raw_uri)
        except (AttributeError, RedfishError):
            pass
        parsed = urlparse(raw_uri)
        path = parsed.path.rstrip("/") or "/"
        canonical = (
            f"{parsed.scheme}://{parsed.netloc}{path}" if parsed.netloc else path
        )
        return f"{canonical}?{parsed.query}" if parsed.query else canonical

    @staticmethod
    def _value_type(value: Any) -> str:
        if value is None:
            return "unknown"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        return "object"

    @staticmethod
    def _interface_kind(
        payload: Mapping[str, Any], item: Mapping[str, Any]
    ) -> Optional[str]:
        text = " ".join(
            str(value)
            for value in (
                payload.get("@odata.type"),
                payload.get("Name"),
                item.get("link_path"),
            )
            if value
        ).lower()
        if "wireless" in text or "wifi" in text:
            return "wireless"
        if "ethernet" in text:
            return "ethernet"
        return None

    @staticmethod
    def _schema_fingerprint(
        resources: Iterable[Mapping[str, Any]], schema_etags: Iterable[str]
    ) -> str:
        types = sorted(
            str(resource.get("odata_type"))
            for resource in resources
            if resource.get("odata_type")
        )
        material = types + sorted(schema_etags)
        return hashlib.sha256("|".join(material).encode()).hexdigest()

