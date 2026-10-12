---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [go, refactor, none]
---
Here's the function that builds our sales report. Add a minimum amount the caller can set: rows below it should be left out entirely, so they aren't listed, don't count toward the row limit, and aren't added to the total. Save the result as `internal/report/report.go`.

```go
package report

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// BuildReport builds the sales report and saves a copy to disk.
func BuildReport(strTitle string, arrRows []map[string]interface{}, intLimit int, bTotals bool, strCurrency string, strOutPath string) string {
	var sb strings.Builder
	sb.WriteString(strTitle + "\n")

	// sort rows by amount, biggest first
	sort.Slice(arrRows, func(i, j int) bool {
		return arrRows[i]["amount"].(float64) > arrRows[j]["amount"].(float64)
	})

	var fltTotal float64
	for i, row := range arrRows {
		if i >= intLimit {
			break
		}
		strName, _ := row["name"].(string)
		fltAmount, _ := row["amount"].(float64)
		fltTotal += fltAmount
		sb.WriteString(fmt.Sprintf("%-20s %10.2f %s\n", strName, fltAmount, strCurrency))
	}

	// add the total line
	if bTotals {
		sb.WriteString(fmt.Sprintf("%-20s %10.2f %s\n", "TOTAL", fltTotal, strCurrency))
	}

	// save a copy next to the other reports
	err := os.MkdirAll(filepath.Dir(strOutPath), 0o755)
	if err != nil {
	}
	err = os.WriteFile(strOutPath, []byte(sb.String()), 0o644)
	_ = err

	return sb.String()
}
```
