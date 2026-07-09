import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

os.environ["MOUNT_PATH"] = "/bridge-palmito"
os.environ["BRIDGE_CONTRACT_ADDRESS_1"] = "0x1111111111111111111111111111111111111111"

import app as bridge_app  # noqa: E402


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            "BRIDGE_DEPOSITS_CSV": os.environ.get("BRIDGE_DEPOSITS_CSV"),
            "BRIDGE_WITHDRAWALS_CSV": os.environ.get("BRIDGE_WITHDRAWALS_CSV"),
            "SCAN_TIME_FILE": os.environ.get("SCAN_TIME_FILE"),
        }
        self.tempdir = tempfile.TemporaryDirectory()
        base_path = Path(self.tempdir.name)
        self.deposits_csv = base_path / "bridge_deposits.csv"
        self.withdrawals_csv = base_path / "bridge_withdrawals.csv"
        self.scan_time_file = base_path / "scan_time.json"

        self.deposits_csv.write_text(
            "Timestamp,Deposit ID,Sender,Recipient,Amount,Tip,Block Height,Query ID,Status,Claimed Timestamp,Query Data,Bridge Contract Address\n"
            "2026-07-09 00:00:00,1,0xsender,tellor1recipient,1000000000000000000,0,123,qid,completed,,qdata,0x1111111111111111111111111111111111111111\n"
            "2026-07-08 00:00:00,2,0xsender2,badrecipient,2000000000000000000,0,124,qid2,in progress,,qdata2,0x2222222222222222222222222222222222222222\n"
        )
        self.withdrawals_csv.write_text(
            "Timestamp,creator,recipient,success,Claimed,txhash,withdraw_id,Amount\n"
            "2026-07-09 01:00:00,tellor1creator,0xrecipient,true,true,0xtx,1,2000000\n"
            "2026-07-09 02:00:00,,,,,,2,\n"
        )
        self.scan_time_file.write_text('{"last_scan": "2026-07-09 03:00:00 UTC"}')

        os.environ["BRIDGE_DEPOSITS_CSV"] = str(self.deposits_csv)
        os.environ["BRIDGE_WITHDRAWALS_CSV"] = str(self.withdrawals_csv)
        os.environ["SCAN_TIME_FILE"] = str(self.scan_time_file)

        self.client = bridge_app.app.test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tempdir.cleanup()

    def test_mounted_deposits_api_returns_transformed_rows(self):
        response = self.client.get("/bridge-palmito/api/v1/deposits?status=completed")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

        payload = response.get_json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["last_scan"], "2026-07-09 03:00:00 UTC")
        self.assertEqual(payload["data"][0]["Deposit ID"], 1)
        self.assertEqual(payload["data"][0]["Amount"], 1.0)
        self.assertEqual(payload["data"][0]["Amount_Raw"], 1000000000000000000)
        self.assertEqual(payload["data"][0]["Contract_Version"], "V1")

    def test_withdrawals_api_filters_claimed_and_converts_amount(self):
        response = self.client.get("/bridge-palmito/api/v1/withdrawals?claimed=true")

        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["data"][0]["withdraw_id"], 1)
        self.assertEqual(payload["data"][0]["Amount_TRB"], 2.0)
        self.assertTrue(payload["data"][0]["Claimed"])

    def test_summary_api_returns_counts_and_totals(self):
        response = self.client.get("/bridge-palmito/api/v1/summary")

        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertEqual(payload["deposits"]["count"], 2)
        self.assertEqual(payload["deposits"]["completed_count"], 1)
        self.assertEqual(payload["deposits"]["total_amount_trb"], 3.0)
        self.assertEqual(payload["withdrawals"]["count"], 2)
        self.assertEqual(payload["withdrawals"]["claimed_count"], 1)

    def test_missing_csv_returns_predictable_api_error(self):
        os.environ["BRIDGE_DEPOSITS_CSV"] = str(Path(self.tempdir.name) / "missing.csv")

        response = self.client.get("/bridge-palmito/api/v1/deposits")

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["error"]["code"], "csv_data_unavailable")
        self.assertEqual(payload["error"]["dataset"], "deposits")

    def test_health_reports_configured_files(self):
        response = self.client.get("/bridge-palmito/health")

        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["files"]["deposits_csv"]["exists"])
        self.assertTrue(payload["files"]["withdrawals_csv"]["exists"])


if __name__ == "__main__":
    unittest.main()
