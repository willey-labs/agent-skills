---
type: llm
focus: files
---
This is the list of files an agent created when asked to add a `/catalog` page, with a product grid and a search filter, to a Next.js App Router project whose routes live in `app/`. Judge only the paths. Ignore project setup files if any were created (`package.json`, `tsconfig.json`, Next, Tailwind or PostCSS config, `next-env.d.ts`, `app/layout.tsx`, global CSS). PASS only if every claim holds; otherwise FAIL and name the claim and the path.

1. The route is `app/catalog/page.tsx`.
2. Every other component or hook created for the catalog sits under a folder named for the catalog feature: a path segment such as `catalog`, `product-catalog` or `products`. For example `app/catalog/_components/ProductGrid.tsx`, `app/catalog/CatalogSearch.tsx`, `src/catalog/ProductCard.tsx`, `src/features/catalog/use-product-search.ts` and `components/catalog/ProductGrid.tsx` pass; `components/ProductCard.tsx`, `src/components/SearchBox.tsx` and `hooks/useProductSearch.ts` fail. A file under a design-system folder named `ui` (such as `components/ui/Input.tsx`) is exempt.
3. Data and type files (the product list, a `Product` type) are not judged on location, only on claim 4.
4. No created file or folder is named `utils`, `util`, `helpers`, `helper`, `common` or `misc`.
