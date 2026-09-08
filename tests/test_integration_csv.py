"""
Unit & Integration Tests for CSV Parser & Ingestion.
"""

import io
from django.test import TestCase
from apps.integration.parsers.csv_parser import parse_csv_file


class CsvParserTests(TestCase):
    def test_valid_csv_parsing(self):
        csv_content = (
            "ma_khach_hang,ten_khach,tong_tien,ngay_tao\n"
            "KH-001,Nguyen Van A,1500000,2026-08-20\n"
            "KH-002,Tran Thi B,2300000,2026-08-21\n"
            "KH-003,Le Van C,850000,2026-08-22\n"
        )
        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        res = parse_csv_file(file_obj)

        self.assertTrue(res["is_valid"])
        self.assertEqual(res["total_rows"], 3)
        self.assertEqual(res["columns"], ["ma_khach_hang", "ten_khach", "tong_tien", "ngay_tao"])
        self.assertEqual(len(res["rows"]), 3)
        self.assertEqual(res["rows"][0]["raw_data"]["ma_khach_hang"], "KH-001")
        self.assertEqual(res["rows"][0]["raw_data"]["tong_tien"], "1500000")
        self.assertTrue(res["rows"][0]["is_valid"])

    def test_csv_with_utf8_sig_and_vietnamese_characters(self):
        csv_content = (
            "mã_đơn,khách_hàng,tổng_thanh_toán,trạng_thái\n"
            "ĐH-001,Nguyễn Thị Mai Lan,1.250.000 đ,Đã hoàn thành\n"
            "ĐH-002,Phạm Quốc Bảo,950.000 đ,Đang giao hàng\n"
        )
        file_obj = io.BytesIO(csv_content.encode("utf-8-sig"))
        res = parse_csv_file(file_obj)

        self.assertTrue(res["is_valid"])
        self.assertEqual(res["total_rows"], 2)
        self.assertEqual(res["rows"][0]["raw_data"]["khách_hàng"], "Nguyễn Thị Mai Lan")
        self.assertEqual(res["rows"][0]["raw_data"]["trạng_thái"], "Đã hoàn thành")

    def test_malformed_csv_row_isolation(self):
        # Row 2 has 5 columns instead of 3; parser should record error on row 2 without crashing
        csv_content = (
            "col_a,col_b,col_c\n"
            "val1,val2,val3\n"
            "bad1,bad2,bad3,extra4,extra5\n"
            "val4,val5,val6\n"
        )
        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        res = parse_csv_file(file_obj)

        self.assertTrue(res["is_valid"])
        self.assertEqual(res["total_rows"], 3)
        self.assertTrue(res["rows"][0]["is_valid"])
        self.assertFalse(res["rows"][1]["is_valid"])
        self.assertIn("column mismatch", res["rows"][1]["errors"][0])
        self.assertTrue(res["rows"][2]["is_valid"])

    def test_empty_csv_file(self):
        file_obj = io.BytesIO(b"   \n  \n")
        res = parse_csv_file(file_obj)

        self.assertFalse(res["is_valid"])
        self.assertEqual(res["total_rows"], 0)
        self.assertIn("no data", res["error_message"].lower())

    def test_csv_duplicate_headers_renamed(self):
        csv_content = (
            "header,header,other\n"
            "1,2,3\n"
        )
        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        res = parse_csv_file(file_obj)

        self.assertTrue(res["is_valid"])
        self.assertEqual(res["columns"], ["header", "header_2", "other"])
        self.assertEqual(res["rows"][0]["raw_data"]["header_2"], "2")

    def test_csv_custom_delimiter(self):
        csv_content = (
            "id;name;price\n"
            "1;Widget A;100\n"
            "2;Widget B;200\n"
        )
        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        res = parse_csv_file(file_obj, delimiter=";")

        self.assertTrue(res["is_valid"])
        self.assertEqual(res["total_rows"], 2)
        self.assertEqual(res["columns"], ["id", "name", "price"])
        self.assertEqual(res["rows"][0]["raw_data"]["name"], "Widget A")
