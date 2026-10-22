"""Tests for learned contracts, target selection, and safe writes."""

import tempfile
import unittest
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.redfish_mcp.contract import ContractResolver
from src.redfish_mcp.store import (
    ContractConflictError,
    RedisContractStore,
    SQLiteContractStore,
)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.lists = {}

    def get(self, key):
        return self.values.get(key)

    def eval(
        self, script, key_count, key, counter_key, expected, raw_document
    ):
        current = json.loads(self.values[key])["revision"] if key in self.values else 0
        if current != int(expected):
            return -1
        document = json.loads(raw_document)
        revision = int(self.values.get(counter_key, 0)) + 1
        self.values[counter_key] = str(revision)
        document["revision"] = revision
        self.values[key] = json.dumps(document)
        return revision

    def delete(self, key):
        self.values.pop(key, None)


class FakeRedfishClient:
    """Small graph-shaped Redfish service used by resolver tests."""

    base_url = "https://bmc.example/redfish/v1"

    def __init__(self):
        self.patch_calls = []
        self.post_calls = []
        self.firmware = "1.0.0"
        self.resources = {
            "/redfish/v1": {
                "@odata.id": "/redfish/v1",
                "@odata.type": "#ServiceRoot.v1_0_0.ServiceRoot",
                "UUID": "target-1",
                "RedfishVersion": "1.20.0",
                "Systems": {"@odata.id": "/redfish/v1/Systems"},
                "Managers": {"@odata.id": "/redfish/v1/Managers"},
                "AccountService": {"@odata.id": "/redfish/v1/AccountService"},
                "External": {"@odata.id": "https://attacker.example/redfish/v1"},
            },
            "/redfish/v1/AccountService": {
                "@odata.id": "/redfish/v1/AccountService",
                "@odata.type": "#AccountService.v1_0_0.AccountService",
                "Accounts": {"@odata.id": "/redfish/v1/AccountService/Accounts"},
            },
            "/redfish/v1/AccountService/Accounts": {
                "@odata.id": "/redfish/v1/AccountService/Accounts",
                "@odata.type": "#ManagerAccountCollection.ManagerAccountCollection",
                "Members": [
                    {"@odata.id": "/redfish/v1/AccountService/Accounts/1"},
                    {"@odata.id": "/redfish/v1/AccountService/Accounts/2"},
                ],
            },
            "/redfish/v1/AccountService/Accounts/1": {
                "@odata.id": "/redfish/v1/AccountService/Accounts/1",
                "@odata.type": "#ManagerAccount.v1_0_0.ManagerAccount",
                "Id": "1",
                "UserName": "alice",
                "RoleId": "Administrator",
            },
            "/redfish/v1/AccountService/Accounts/2": {
                "@odata.id": "/redfish/v1/AccountService/Accounts/2",
                "@odata.type": "#ManagerAccount.v1_0_0.ManagerAccount",
                "Id": "2",
                "UserName": "bob",
                "RoleId": "Operator",
            },
            "/redfish/v1/Managers": {
                "@odata.id": "/redfish/v1/Managers",
                "@odata.type": "#ManagerCollection.ManagerCollection",
                "Members": [{"@odata.id": "/redfish/v1/Managers/1"}],
            },
            "/redfish/v1/Managers/1": {
                "@odata.id": "/redfish/v1/Managers/1",
                "@odata.type": "#Manager.v1_0_0.Manager",
                "Id": "1",
                "Name": "BMC",
            },
            "/redfish/v1/Systems": {
                "@odata.id": "/redfish/v1/Systems",
                "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
                "Members": [{"@odata.id": "/redfish/v1/Systems/Wired"}],
                "Members@odata.nextLink": "/redfish/v1/Systems?$skip=1",
            },
            "/redfish/v1/Systems?$skip=1": {
                "@odata.id": "/redfish/v1/Systems",
                "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
                "Members": [{"@odata.id": "/redfish/v1/Systems/Wireless"}],
            },
            "/redfish/v1/Systems/Wired": self._interface(
                "Wired", "Ethernet Adapter", "#EthernetInterface.v1_0_0.EthernetInterface"
            ),
            "/redfish/v1/Systems/Wireless": self._interface(
                "Wireless", "Wireless Adapter", "#EthernetInterface.v1_0_0.EthernetInterface"
            ),
            "/redfish/v1/Systems/Wired/Settings": {
                "@odata.id": "/redfish/v1/Systems/Wired/Settings",
                "@odata.type": "#EthernetInterface.v1_0_0.EthernetInterface",
                "@odata.etag": '"Wired-settings-1"',
                "Id": "Wired",
                "Name": "Pending Wired Settings",
                "IPAddress": "192.0.2.1",
                "IPAddress@Redfish.AllowableValues": ["192.0.2.1", "192.0.2.2"],
                "Status": {"State": "Enabled"},
            },
            "/redfish/v1/Systems/Wireless/ResetActionInfo": {
                "@odata.id": "/redfish/v1/Systems/Wireless/ResetActionInfo",
                "@odata.type": "#ActionInfo.v1_0_0.ActionInfo",
                "Parameters": [{
                    "Name": "ResetType",
                    "Required": True,
                    "DataType": "String",
                    "AllowableValues": ["GracefulRestart"],
                }],
            },
        }
        self.resources["/redfish/v1/Systems/Wired"]["@Redfish.Settings"] = {
            "SettingsObject": {
                "@odata.id": "/redfish/v1/Systems/Wired/Settings"
            },
            "SupportedApplyTimes": ["Immediate"],
        }
        self.resources["/redfish/v1/Systems/Wireless"]["Actions"] = {
            "#ComputerSystem.Reset": {
                "target": "/redfish/v1/Systems/Wireless/Actions/ComputerSystem.Reset",
                "@Redfish.ActionInfo": "/redfish/v1/Systems/Wireless/ResetActionInfo",
            }
        }

    @staticmethod
    def _interface(identifier: str, name: str, odata_type: str) -> Dict[str, Any]:
        uri = f"/redfish/v1/Systems/{identifier}"
        return {
            "@odata.id": uri,
            "@odata.type": odata_type,
            "@odata.etag": f'"{identifier}-1"',
            "Id": identifier,
            "Name": name,
            "IPAddress": "192.0.2.1",
            "IPAddress@Redfish.AllowableValues": ["192.0.2.1", "192.0.2.2"],
            "Status": {"State": "Enabled"},
            "Links": {
                "Collection": {"@odata.id": "/redfish/v1/Systems"},
                "Self": {"@odata.id": f"https://bmc.example{uri}"},
                "RelatedItem": [{"@odata.id": f"{uri}#/Status"}],
            },
        }

    def get(self, endpoint: str) -> Dict[str, Any]:
        data, _, _ = self.get_with_headers(endpoint)
        return data

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("https://") and not endpoint.startswith(
            "https://bmc.example/"
        ):
            from src.redfish_mcp.exceptions import RedfishClientError

            raise RedfishClientError("off-origin")
        if endpoint.startswith("https://"):
            return endpoint
        if endpoint.startswith("/redfish/v1"):
            return f"https://bmc.example{endpoint}"
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def get_with_headers(self, endpoint: str):
        key = "/redfish/v1" if endpoint == "" else endpoint
        if key not in self.resources:
            from src.redfish_mcp.exceptions import RedfishClientError

            raise RedfishClientError("not found", status_code=404)
        data = dict(self.resources[key])
        if key == "/redfish/v1/Managers/1":
            data["FirmwareVersion"] = self.firmware
        headers = {}
        if data.get("@odata.etag"):
            headers["ETag"] = data["@odata.etag"]
        if "IPAddress" in data:
            headers["Allow"] = "GET, PATCH"
        return data, headers, 200

    def patch_with_status(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ):
        self.patch_calls.append((endpoint, data, dict(headers or {})))
        return {}, 204

    def post_with_status(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ):
        self.post_calls.append((endpoint, data, dict(headers or {})))
        return {}, 204


class TestSQLiteContractStore(unittest.TestCase):
    def test_revision_compare_and_swap_and_audit_survives_invalidate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteContractStore(str(Path(directory) / "contracts.sqlite"))
            self.assertEqual(store.put("target:role", {"value": 1}, 0), 1)
            with self.assertRaises(ContractConflictError):
                store.put("target:role", {"value": 2}, 0)
            audit_id = store.append_audit(
                {"contract_key": "target:role", "operation": "PATCH"}
            )
            store.invalidate("target:role")
            self.assertIsNone(store.get("target:role"))
            self.assertEqual(store.put("target:role", {"value": 3}, 0), 2)
            self.assertEqual(store.list_audits("target:role")[0]["audit_id"], audit_id)

    def test_redis_compare_and_swap_with_fake_client(self):
        store = RedisContractStore.__new__(RedisContractStore)
        store._redis = FakeRedis()
        self.assertEqual(store.put("target:role", {"value": 1}, 0), 1)
        self.assertEqual(store.get("target:role")["revision"], 1)
        with self.assertRaises(ContractConflictError):
            store.put("target:role", {"value": 2}, 0)
        store.invalidate("target:role")
        self.assertIsNone(store.get("target:role"))
        self.assertEqual(store.put("target:role", {"value": 3}, 0), 2)

    @unittest.skipUnless(os.getenv("REDIS_URL"), "REDIS_URL is not set")
    def test_live_redis_connection_when_configured(self):
        store = RedisContractStore(os.environ["REDIS_URL"])
        self.assertIsNotNone(store)


class TestContractResolver(unittest.TestCase):
    def setUp(self):
        self.client = FakeRedfishClient()
        self.store = SQLiteContractStore(":memory:")
        self.resolver = ContractResolver(
            self.client,
            self.store,
            probe_ttl_seconds=0,
            max_resources=50,
        )

    def test_ambiguous_write_returns_candidates_without_writing(self):
        result = self.resolver.set_properties({"IPAddress": "192.0.2.2"})
        self.assertEqual(result["status"], "ambiguous_target")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(self.client.patch_calls, [])

    def test_context_selector_builds_minimal_patch_with_fresh_etag(self):
        result = self.resolver.set_properties(
            {"IPAddress": "192.0.2.2"},
            {"interface_kind": "wireless"},
        )
        self.assertEqual(result["status"], "updated")
        endpoint, body, headers = self.client.patch_calls[0]
        self.assertEqual(endpoint, "/redfish/v1/Systems/Wireless")
        self.assertEqual(body, {"IPAddress": "192.0.2.2"})
        self.assertEqual(headers, {"If-Match": '"Wireless-1"'})
        self.assertNotIn("Status", body)
        self.assertNotIn("@odata.id", body)

    def test_selector_values_are_exact_not_substrings(self):
        result = self.resolver.set_properties(
            {"IPAddress": "192.0.2.2"}, {"Id": "Wire"}
        )
        self.assertEqual(result["status"], "not_found")
        self.assertEqual(self.client.patch_calls, [])

    def test_candidate_from_ambiguous_result_can_be_selected(self):
        ambiguous = self.resolver.set_properties({"IPAddress": "192.0.2.2"})
        candidate = next(
            item
            for item in ambiguous["candidates"]
            if item["interface_kind"] == "ethernet"
        )
        result = self.resolver.set_properties(
            {"IPAddress": "192.0.2.2"},
            candidate_id=candidate["candidate_id"],
        )
        self.assertEqual(result["status"], "updated")
        self.assertEqual(
            self.client.patch_calls[0][0], "/redfish/v1/Systems/Wired/Settings"
        )

    def test_action_arguments_are_validated_and_audited(self):
        rejected = self.resolver.invoke_action(
            "Reset", {"ResetType": "ForceRestart"}, {"Id": "Wireless"}
        )
        self.assertEqual(rejected["status"], "rejected")
        result = self.resolver.invoke_action(
            "Reset", {"ResetType": "GracefulRestart"}, {"Id": "Wireless"}
        )
        self.assertEqual(result["status"], "invoked")
        self.assertEqual(
            self.client.post_calls[0][0],
            "/redfish/v1/Systems/Wireless/Actions/ComputerSystem.Reset",
        )
        audits = self.store.list_audits("target-1:anonymous")
        self.assertEqual(audits[-1]["contract_revision"], result["contract_revision"])

    def test_action_suffix_must_not_choose_between_duplicate_names(self):
        self.client.resources["/redfish/v1/Systems/Wireless"]["Actions"][
            "#Oem.Reset"
        ] = {
            "target": "/redfish/v1/Systems/Wireless/Actions/Oem.Reset"
        }
        result = self.resolver.invoke_action(
            "Reset", {}, {"Id": "Wireless"}
        )
        self.assertEqual(result["status"], "ambiguous_action")
        self.assertEqual(self.client.post_calls, [])

    def test_write_without_fresh_etag_is_refused(self):
        del self.client.resources[
            "/redfish/v1/Systems/Wireless"
        ]["@odata.etag"]
        result = self.resolver.set_properties(
            {"IPAddress": "192.0.2.2"}, {"Id": "Wireless"}
        )
        self.assertEqual(result["status"], "rejected")
        self.assertIn("ETag", result["message"])
        self.assertEqual(self.client.patch_calls, [])

    def test_unexplored_failed_link_prevents_write(self):
        self.client.resources["/redfish/v1"]["Broken"] = {
            "@odata.id": "/redfish/v1/Broken"
        }
        result = self.resolver.set_properties(
            {"IPAddress": "192.0.2.2"}, {"Id": "Wireless"}
        )
        self.assertEqual(result["status"], "budget_limited")
        self.assertEqual(self.client.patch_calls, [])

    def test_failed_action_info_refuses_action(self):
        del self.client.resources[
            "/redfish/v1/Systems/Wireless/ResetActionInfo"
        ]
        result = self.resolver.invoke_action(
            "Reset", {}, {"Id": "Wireless"}
        )
        self.assertEqual(result["status"], "rejected")
        self.assertIn("failed", result["message"])
        self.assertEqual(self.client.post_calls, [])

    def test_unannotated_settings_leaf_is_not_assumed_writable(self):
        self.client.resources["/redfish/v1/Systems/Wired/Settings"][
            "SerialNumber"
        ] = "read-only"
        result = self.resolver.find_capabilities(
            "SerialNumber", {"Id": "Wired"}
        )
        self.assertEqual(result["status"], "not_found")

    def test_json_schema_requires_explicit_write_permission(self):
        writable = self.resolver._writable_from_json_schema(
            {
                "properties": {
                    "BootProgress": {"$ref": "#/definitions/BootProgress"},
                    "Alias": {
                        "type": ["string", "null"],
                        "readonly": False,
                    },
                    "SerialNumber": {"type": "string", "readonly": True},
                }
            },
            "Example",
        )
        self.assertEqual(writable, {
            "Alias": {"type": "string", "allowable_values": None}
        })

    def test_schema_cache_is_copied_per_resource(self):
        self.resolver._schema_cache["#Example.v1_0_0.Example"] = {
            "Alias": {"type": "string", "allowable_values": None}
        }
        first = self.resolver._schema_writable("#Example.v1_0_0.Example")
        first["Other"] = {"type": "string", "allowable_values": None}
        second = self.resolver._schema_writable("#Example.v1_0_0.Example")
        self.assertNotIn("Other", second)

    def test_firmware_change_invalidates_contract_and_reexplores(self):
        self.resolver.find_capabilities("IPAddress")
        first_revision = self.store.get("target-1:anonymous")["revision"]
        self.client.firmware = "2.0.0"
        result = self.resolver.set_properties(
            {"IPAddress": "192.0.2.2"}, {"Id": "Wired"}
        )
        self.assertEqual(result["status"], "updated")
        self.assertGreater(result["contract_revision"], first_revision)
        current = self.store.get("target-1:anonymous")
        self.assertEqual(current["generation"]["firmware"]["1"], "2.0.0")
        self.assertGreaterEqual(first_revision, 1)

    def test_incompatible_contract_format_is_rebuilt(self):
        self.store.put(
            "target-1:anonymous",
            {
                "format_version": 999,
                "generation": {},
                "resources": {},
                "visited": [],
                "frontier": [],
            },
            0,
        )
        self.resolver.find_capabilities("IPAddress")
        current = self.store.get("target-1:anonymous")
        self.assertEqual(current["format_version"], 1)
        self.assertGreater(current["revision"], 1)

    def test_roles_have_separate_contract_keys(self):
        shared_store = SQLiteContractStore(":memory:")
        alice = ContractResolver(
            self.client, shared_store, username="alice", probe_ttl_seconds=0
        )
        bob = ContractResolver(
            self.client, shared_store, username="bob", probe_ttl_seconds=0
        )
        alice.find_capabilities("IPAddress")
        bob.find_capabilities("IPAddress")
        self.assertIsNotNone(shared_store.get("target-1:role:Administrator"))
        self.assertIsNotNone(shared_store.get("target-1:role:Operator"))

    def test_traversal_skips_cycles_and_indexes_fragment(self):
        self.resolver.find_capabilities("IPAddress")
        contract = self.store.get("target-1:anonymous")
        wired = next(
            resource
            for resource in contract["resources"].values()
            if resource["uri"] == "/redfish/v1/Systems/Wired"
        )
        self.assertEqual(
            wired["fragment_references"][0]["fragment"], "/Status"
        )
        visited = contract["visited"]
        self.assertEqual(len(visited), len(set(visited)))


if __name__ == "__main__":
    unittest.main()
