import argparse
import json
import sys

import pytest

from main import parse_args, check_date, logs_processing, report_average


@pytest.mark.parametrize(
    "argv,expected_file,expected_report,expected_name",
    [
        (["main.py", "--file", "f.log", "--report", "average"], ["f.log"], "average", None),
        (["main.py", "--file", "f1.log", "f2.log", "--report", "average"], ["f1.log", "f2.log"], "average", None),
        (["main.py", "--name", "test_name", "--report", "average", "--file", "f.log"], ["f.log"], "average",
         "test_name"),
        (["main.py", "--file", "f.log", "--report", "average", "--name", "name_test"], ["f.log"], "average",
         "name_test"),

    ],
    ids=[
        "single_file_no_report_name",
        "multiple_files_no_report_name",
        "random_order_single_file_with_report_name",
        "single_file_with_name_name_test"
    ]
)
def test_parse_args_valid(monkeypatch, argv, expected_file, expected_report, expected_name):
    monkeypatch.setattr(sys, "argv", argv)
    args = parse_args()
    assert args.file == expected_file
    assert args.report == expected_report
    assert args.name == expected_name


@pytest.mark.parametrize(
    "argv",
    [
        (["main.py", "--report", "average"]),
        (["main.py", "--file", "f.log"]),
        (["main.py", "--file", "f.log", "--report", "user_agent"]),
        (["main.py", "--file", "f.log", "--report", "average", "--extra", "user_ids"]),
        (["main.py"]),
    ],
    ids=[
        "missing_file",
        "missing_report",
        "invalid_report_choice",
        "unknown_argument",
        "no_arguments"
    ]
)
def test_parse_args_invalid(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit):
        parse_args()


@pytest.mark.parametrize(
    "input_date,expected_date",
    [
        ("2025-12-03", "2025-12-03"),
        ("2025/12/03", "2025-12-03"),
        ("2025:12:03", "2025-12-03"),
        ("2025.12.03", "2025-12-03"),
        ("2025;12;03", "2025-12-03"),
        ("20251203", "2025-12-03"),
    ],
    ids=[
        "date_format_2025-12-03",
        "date_format_2025/12/03",
        "date_format_2025:12:03",
        "date_format_2025.12.03",
        "date_format_2025;12;03",
        "date_format_20251203"
    ]
)
def test_check_date_correct(input_date, expected_date):
    result = check_date(input_date)
    assert result == expected_date


@pytest.mark.parametrize(
    "input_date",
    [
        "03-12-2025",
        "2025-12-32",
        "2025.13.12",
        "2025/99/99",
        "2025-12,99",
        "abcd-ef-gh",
        "abcdefgh",
        "",
    ],
    ids=[
        "date_format_03-12-2025",
        "date_format_2025-12-32",
        "date_format_2025.13.12",
        "date_format_2025/99/99",
        "date_format_2025-12,99",
        "date_format_abcd-ef-gh",
        "date_format_abcdefgh",
        "empty_date"
    ]
)
def test_check_date_incorrect(input_date):
    with pytest.raises(argparse.ArgumentTypeError):
        check_date(input_date)


@pytest.mark.parametrize(
    "log_lines,date_filter,expected_urls",
    [
        (
                [
                    json.dumps({"@timestamp": "2025-12-03T12:00:00", "url": "/api/test1", "response_time": 1}),
                    json.dumps({"@timestamp": "2025-12-04T12:00:00", "url": "/api/test2", "response_time": 2}),
                    "not_a_json_line",
                    json.dumps({"@timestamp": "2025-12-03T13:00:00", "url": "/api/test3", "response_time": 3})
                ],
                None,
                ["/api/test1", "/api/test2", "/api/test3"]
        ),
        (
                [
                    json.dumps({"@timestamp": "2025-12-03T12:00:00", "url": "/api/test1", "response_time": 1}),
                    json.dumps({"@timestamp": "2025-12-04T12:00:00", "url": "/api/test2", "response_time": 2}),
                    "not_a_json_line",
                    json.dumps({"@timestamp": "2025-12-05T13:00:00", "url": "/api/test3", "response_time": 3})
                ],
                "2025-12-05",
                ["/api/test3"]
        ),
        (
                [
                    json.dumps({"@timestamp": "2025-12-03T12:00:00", "url": "/api/test1", "response_time": 1}),
                    json.dumps({"@timestamp": "2025-12-04T12:00:00", "url": "/api/test2", "response_time": 2}),
                    json.dumps({"@timestamp": "2025-12-03T13:00:00", "url": "/api/test3", "response_time": 3})
                ],
                "2025-12-03",
                ["/api/test1", "/api/test3"]
        )
    ],
    ids=[
        "no_date_filter_and_not_json_line",
        "with_date_filter_and_not_json_line",
        "with_date_filter"
    ]
)
def test_logs_processing_valid(tmp_path, log_lines, date_filter, expected_urls):
    log_file = tmp_path / "test.log"
    log_file.write_text("\n".join(log_lines))

    logs = logs_processing([str(log_file)], date_filter=date_filter)
    urls = [log["url"] for log in logs]
    assert urls == expected_urls


def test_logs_processing_missing_file(tmp_path, capsys):
    missing_file = tmp_path / "missing.log"
    result = logs_processing([str(missing_file)])

    assert result == []

    captured = capsys.readouterr()
    assert f"Error caused with {missing_file}" in captured.out


def test_report_average():
    logs = [
        {"url": "/api/test1", "response_time": 1.0},
        {"url": "/api/test1", "response_time": 3.0},
        {"url": "/api/test2", "response_time": 2},
        {"url": "/api/test3", "response_time": 4.524},
        {"url": "/api/test2", "response_time": 2.5},
    ]

    table = report_average(logs)

    assert "/api/test1" in table
    assert "/api/test2" in table
    assert "/api/test3" in table

    assert "2" in table
    assert "2.25" in table
    assert "4.524" in table

