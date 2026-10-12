---
type: llm
focus:
  source: file
  path: src/features/orders/OrdersScreen.tsx
---
The file is a React Native screen that lists orders loaded through a `fetchOrders` prop. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (date format, styling, unmount handling, what shows while a retry is loading) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. On mount it calls `fetchOrders` and shows a loading indicator (such as `ActivityIndicator`) until that first call settles.
2. When `fetchOrders` rejects, it shows an error message and a Retry button whose press calls `fetchOrders` again.
3. When `fetchOrders` resolves to an empty array, it shows "No orders yet".
4. Otherwise it renders a `FlatList` (or `SectionList`) with one row per order keyed by `id`, each showing the date, the status and the total with a `$` sign, thousands separators and two decimals.
5. Pull-to-refresh is wired through the list's `refreshing` and `onRefresh` props or a `RefreshControl`; refreshing calls `fetchOrders` again and replaces the list with the result, and when the reload fails the error state shows and the refreshing indicator does not stay on.
6. The `Order` type is declared in the file and used for the prop and for the loaded list.
