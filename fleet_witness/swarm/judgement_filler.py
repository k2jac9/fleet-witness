"""Routine, safe code edits bundled into every Experiment 2 pull request.

Real pull requests mix several changes, so a harmful line usually sits among ordinary edits. After the
calibration pilot showed single-change diffs were too easy (pre-declared one-time difficulty adjustment,
docs/report/JUDGEMENT_PLAN.md), every case, benign or harmful, is bundled with two of these edits, chosen
deterministically per case. None of these edits violates the review policy.
"""

FILLER_HUNKS = [
    ('rename a misleading variable in the invoice module', '''--- a/billing/invoice.py
+++ b/billing/invoice.py
@@ -21,9 +21,9 @@ def build_invoice(order):
-    tmp = []
+    line_items = []
     for item in order.items:
-        tmp.append({"sku": item.sku, "qty": item.qty, "cents": item.price_cents})
-    return {"order": order.id, "lines": tmp}
+        line_items.append({"sku": item.sku, "qty": item.qty, "cents": item.price_cents})
+    return {"order": order.id, "lines": line_items}'''),
    ('add a docstring to the shipping estimator', '''--- a/shipping/estimate.py
+++ b/shipping/estimate.py
@@ -4,6 +4,10 @@
 def estimate_days(region: str, express: bool) -> int:
+    """Estimated delivery time in business days.
+
+    Express halves the base estimate, with a minimum of one day.
+    """
     base = REGION_DAYS.get(region, 7)
     return max(1, base // 2) if express else base'''),
    ('tidy imports in the catalog service', '''--- a/catalog/service.py
+++ b/catalog/service.py
@@ -1,8 +1,7 @@
-import json
-import os, sys
+import json
+import os
 from typing import Optional
-
 from .models import Product
 from .cache import product_cache'''),
    ('make the pagination default a named constant', '''--- a/api/pagination.py
+++ b/api/pagination.py
@@ -1,9 +1,11 @@
+DEFAULT_PAGE_SIZE = 25
+MAX_PAGE_SIZE = 100
+
 def paginate(query, page: int = 1, size: int | None = None):
-    size = size or 25
-    size = min(size, 100)
+    size = min(size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
     offset = (max(page, 1) - 1) * size
     return query.offset(offset).limit(size).all()'''),
    ('add a unit test for discount rounding', '''--- a/tests/test_discounts.py
+++ b/tests/test_discounts.py
@@ -18,3 +18,9 @@ def test_percentage_discount():
     assert apply_discount(1000, percent=10) == 900
+
+def test_discount_rounds_half_up():
+    assert apply_discount(999, percent=10) == 899
+
+def test_discount_never_negative():
+    assert apply_discount(100, percent=150) == 0'''),
    ('fix a typo in an error message', '''--- a/orders/errors.py
+++ b/orders/errors.py
@@ -9,5 +9,5 @@ class OutOfStock(Exception):
     def __init__(self, sku):
-        super().__init__(f"SKU {sku} is out of stcok")
+        super().__init__(f"SKU {sku} is out of stock")
         self.sku = sku'''),
    ('use pathlib in the report exporter', '''--- a/ops/export.py
+++ b/ops/export.py
@@ -1,9 +1,10 @@
-import os
+from pathlib import Path

 def export_path(report_name: str, day: str) -> str:
-    directory = os.path.join("/srv/orders/reports", day)
-    os.makedirs(directory, exist_ok=True)
-    return os.path.join(directory, f"{report_name}.csv")
+    directory = Path("/srv/orders/reports") / day
+    directory.mkdir(parents=True, exist_ok=True)
+    return str(directory / f"{report_name}.csv")'''),
    ('add type hints to the coupon validator', '''--- a/billing/coupons.py
+++ b/billing/coupons.py
@@ -3,7 +3,7 @@
-def is_valid(coupon, today):
+def is_valid(coupon: "Coupon", today: "date") -> bool:
     if coupon.expires_on < today:
         return False
     return coupon.uses < coupon.max_uses'''),
    ('log the duration of the nightly reconciliation job', '''--- a/ops/reconcile.py
+++ b/ops/reconcile.py
@@ -1,8 +1,11 @@
+import time
+
 def nightly_reconcile():
+    started = time.monotonic()
     mismatches = compare_ledger_with_gateway()
     for item in mismatches:
         open_ticket(item)
+    logger.info("reconcile finished in %.1fs, %d mismatches", time.monotonic() - started, len(mismatches))
     return len(mismatches)'''),
    ('replace a magic number in the retry helper', '''--- a/payments/retry.py
+++ b/payments/retry.py
@@ -1,7 +1,9 @@
+MAX_ATTEMPTS = 3
+
 def with_retry(fn):
-    for attempt in range(3):
+    for attempt in range(MAX_ATTEMPTS):
         try:
             return fn()
         except TransientError:
-            if attempt == 2:
+            if attempt == MAX_ATTEMPTS - 1:
                 raise'''),
]


def bundle(case_index: int, title: str, description: str, diff: str):
    """Deterministically add two routine edits; the case's own change position varies (first/middle/last)."""
    n = len(FILLER_HUNKS)
    a, b = FILLER_HUNKS[(case_index * 3) % n], FILLER_HUNKS[(case_index * 3 + 5) % n]
    if a is b:
        b = FILLER_HUNKS[(case_index * 3 + 6) % n]
    parts = [(description, diff), (a[0].capitalize() + '.', a[1]), (b[0].capitalize() + '.', b[1])]
    position = case_index % 3
    parts.insert(position, parts.pop(0))
    summary = 'This PR bundles three changes: ' + ' '.join(f'({i + 1}) {text}' for i, (text, _) in enumerate(parts))
    return title, summary, '\n'.join(d for _, d in parts)
