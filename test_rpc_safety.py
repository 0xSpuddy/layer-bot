import csv
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from layerbot.utils.ethereum_rpc import FallbackHTTPProvider, RequestSpacer
from layerbot.utils.query_layer import get_claimed_deposit_ids
from layerbot.bridge_info import update_withdrawal_status


class EthereumRpcFallbackTests(unittest.TestCase):
    @patch("layerbot.utils.ethereum_rpc.HTTPProvider")
    def test_rate_limit_response_uses_fallback(self, provider_class):
        primary = Mock()
        fallback = Mock()
        primary.make_request.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32005, "message": "rate limit exceeded"},
        }
        fallback.make_request.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0x1",
        }
        provider_class.side_effect = [primary, fallback]

        provider = FallbackHTTPProvider(
            ["https://primary.invalid", "https://fallback.invalid"],
            10,
            request_interval=0,
        )

        self.assertEqual(provider.make_request("eth_chainId", []), fallback.make_request.return_value)
        self.assertEqual(provider._active_index, 1)

    @patch("layerbot.utils.ethereum_rpc.HTTPProvider")
    def test_is_connected_uses_active_endpoint(self, provider_class):
        primary = Mock()
        primary.make_request.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "erigon/3.5.5",
        }
        provider_class.return_value = primary

        provider = FallbackHTTPProvider(
            ["https://primary.invalid"],
            10,
            request_interval=0,
        )

        self.assertTrue(provider.is_connected())
        primary.make_request.assert_called_once_with("web3_clientVersion", [])

    @patch("layerbot.utils.ethereum_rpc.time.sleep")
    @patch(
        "layerbot.utils.ethereum_rpc.time.monotonic",
        side_effect=[10.0, 10.0, 10.25, 11.0],
    )
    def test_request_spacer_waits_for_remaining_interval(self, monotonic, sleep):
        spacer = RequestSpacer(1)

        spacer.wait()
        spacer.wait()

        sleep.assert_called_once_with(0.75)


class ClaimedDepositQueryTests(unittest.TestCase):
    def test_completed_deposits_are_not_queried_again(self):
        with tempfile.NamedTemporaryFile(mode="w", newline="", delete=False) as csv_file:
            path = csv_file.name
            writer = csv.DictWriter(
                csv_file,
                fieldnames=["Deposit ID", "Status", "Claimed", "Claimed Timestamp"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Deposit ID": "32",
                    "Status": "completed",
                    "Claimed": "yes",
                    "Claimed Timestamp": "2026-08-12 15:00:00",
                }
            )
            writer.writerow(
                {
                    "Deposit ID": "33",
                    "Status": "in progress",
                    "Claimed": "no",
                    "Claimed Timestamp": "",
                }
            )

        env = {
            "LAYER_RPC_URL": "http://layer.invalid",
            "BRIDGE_DEPOSITS_CSV": path,
            "BRIDGE_CLAIM_CHECK_LIMIT": "25",
        }
        result = Mock(stdout="claimed: false\n", stderr="")
        try:
            with patch.dict(os.environ, env, clear=False), patch(
                "layerbot.utils.query_layer.subprocess.run", return_value=result
            ) as run:
                claimed_ids = get_claimed_deposit_ids()

            self.assertEqual(claimed_ids, {"32"})
            self.assertEqual(run.call_count, 1)
            self.assertIn("33", run.call_args.args[0])
            self.assertNotIn("32", run.call_args.args[0])
        finally:
            os.unlink(path)


class WithdrawalQueryTests(unittest.TestCase):
    def test_claimed_withdrawals_are_not_queried_again(self):
        with tempfile.NamedTemporaryFile(mode="w", newline="", delete=False) as csv_file:
            path = csv_file.name
            writer = csv.DictWriter(csv_file, fieldnames=["withdraw_id", "Claimed"])
            writer.writeheader()
            writer.writerow({"withdraw_id": "1", "Claimed": "True"})
            writer.writerow({"withdraw_id": "2", "Claimed": "False"})

        env = {
            "BRIDGE_WITHDRAWALS_CSV": path,
            "BRIDGE_CONTRACT_ADDRESS_CURRENT": "0x0000000000000000000000000000000000000001",
        }
        w3 = Mock()
        try:
            with patch.dict(os.environ, env, clear=True), patch(
                "layerbot.bridge_info.get_ethereum_web3", return_value=w3
            ), patch("layerbot.bridge_info.load_abi", return_value=[]), patch(
                "layerbot.bridge_info.check_withdrawal_status", return_value=False
            ) as check:
                update_withdrawal_status()

            self.assertEqual(check.call_count, 1)
            self.assertEqual(check.call_args.args[2], 2)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
