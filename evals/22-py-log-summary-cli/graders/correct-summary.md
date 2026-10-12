---
type: llm
focus:
  source: file
  path: log_summary.py
---
The file is a command-line script that summarizes a web server access log. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (output layout, a missing file, ties among the top paths, which percentile method) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. It takes the log file path as a positional argument through `argparse`.
2. For a line in the given format it reads the request path, the status and the response time; the path drops the query string, so `/api/orders?page=2` counts as `/api/orders`.
3. It counts requests per status class 2xx, 3xx, 4xx and 5xx by the status code's first digit.
4. It prints the 5 most requested paths with their counts, most requested first.
5. It prints the 95th percentile of the response times in milliseconds (seconds × 1000), by nearest rank, linear interpolation or `statistics.quantiles`.
6. A line that does not fit the format, including one whose status or response time is not a number, is counted as skipped and does not stop the run, and the skipped count is printed.
7. A skipped line adds nothing to the status counts, the path counts or the response times.
8. A log with no valid lines prints its summary without raising, showing the percentile as absent, zero or similar.
