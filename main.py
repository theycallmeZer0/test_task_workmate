import argparse
import json
from collections import defaultdict
from tabulate import tabulate
from datetime import datetime
import re


def parse_args():
    parser = argparse.ArgumentParser(description="Log file analyzer")
    parser.add_argument("--name", help="Report name")
    parser.add_argument("--file", nargs="+", required=True, help="Path(s) to log file(s)")
    parser.add_argument("--report", required=True, choices=["average"], help="Report type")
    parser.add_argument("--date", type=check_date, help="Filter by date (YYYY-MM-DD)")
    return parser.parse_args()


def check_date(date_str):

    if re.fullmatch(r"\d{8}", date_str):
        normalized = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        normalized = re.sub(r"[-/:.;]", "-", date_str)

    try:
        dt = datetime.strptime(normalized, "%Y-%m-%d").date()
        return dt.isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date: '{date_str}'. Expected a valid date with separators or no separators"
        )


def logs_processing(files, date_filter=None):
    logs = []
    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        callback = json.loads(line.strip())
                        if date_filter:
                            timestamp = callback.get("@timestamp")
                            if timestamp and timestamp.startswith(date_filter):
                                logs.append(callback)
                        else:
                            logs.append(callback)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error caused with {file}: {e}")
    return logs


def report_average(logs):
    stats = defaultdict(lambda: {"count": 0, "total_time": 0.0})
    for log in logs:
        url = log.get("url")
        resp_time = log.get("response_time", 0)
        if url and resp_time:
            stats[url]["count"] += 1
            stats[url]["total_time"] += resp_time
        else:
            continue

    table = []
    for url, data in stats.items():
        avg_time = data["total_time"] / data["count"]
        table.append([url, data["count"], round(avg_time, 3)])

    return tabulate(table, headers=["Endpoint", "Count", "Avg Response Time"], tablefmt="simple")


reports = {
    "average": report_average
    # here you can call another report by setting it name and function name
}


def main():
    args = parse_args()

    logs = logs_processing(args.file, args.date)

    if not logs:
        print("No logs found")
        return

    if args.name:
        print(f"Report {args.name}")
    report_func = reports.get(args.report)
    print(report_func(logs))


if __name__ == "__main__":
    main()
