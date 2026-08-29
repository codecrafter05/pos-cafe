"""Datetimes must reach the browser tagged as UTC.

Timestamps are stored naive-UTC. A naive ISO string ("2026-08-27T21:30:00") is
read by ``new Date()`` as *local* time per the ECMAScript spec, which rendered
every sale three hours early in Bahrain. The explicit "Z" is the fix.

    .venv/bin/python -m unittest discover -s tests -v
"""

import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.core.time import as_bahrain, iso_utc
from app.schemas.orders import OrderOut


def _order(created_at):
    return OrderOut(
        id=1, daily_order_number=7, user_id=2,
        customer_name=None, customer_phone=None, customer_car_plate=None,
        total_amount=Decimal("1.700"), total_cost=Decimal("0.400"),
        profit=Decimal("1.300"), payment_method="cash", source="device",
        status="delivered", notes=None, created_at=created_at,
    )


class IsoUtcTestCase(unittest.TestCase):
    def test_naive_value_is_tagged_as_utc(self):
        self.assertEqual(iso_utc(datetime(2026, 8, 27, 21, 30, 0)), "2026-08-27T21:30:00Z")

    def test_aware_utc_value_uses_z_not_offset(self):
        dt = datetime(2026, 8, 27, 21, 30, tzinfo=timezone.utc)
        self.assertEqual(iso_utc(dt), "2026-08-27T21:30:00Z")

    def test_aware_non_utc_value_is_converted(self):
        """A Bahrain-aware 00:30 is 21:30 UTC the previous day."""
        dt = as_bahrain(datetime(2026, 8, 27, 21, 30))
        self.assertEqual(dt.hour, 0)
        self.assertEqual(iso_utc(dt), "2026-08-27T21:30:00Z")

    def test_microseconds_are_preserved(self):
        dt = datetime(2026, 8, 27, 21, 30, 0, 123456)
        self.assertEqual(iso_utc(dt), "2026-08-27T21:30:00.123456Z")

    def test_never_emits_a_bare_naive_string(self):
        for month, day, hour in [(1, 1, 0), (6, 15, 12), (12, 31, 23)]:
            out = iso_utc(datetime(2026, month, day, hour, 5, 9))
            self.assertTrue(out.endswith("Z"), out)


class OrderOutSerializationTestCase(unittest.TestCase):
    def test_created_at_is_serialized_with_z(self):
        payload = json.loads(_order(datetime(2026, 8, 27, 21, 30, 0)).model_dump_json())
        self.assertEqual(payload["created_at"], "2026-08-27T21:30:00Z")

    def test_python_mode_keeps_a_real_datetime(self):
        """Only JSON output is rewritten — server-side callers still get a datetime."""
        value = _order(datetime(2026, 8, 27, 21, 30, 0)).model_dump()["created_at"]
        self.assertIsInstance(value, datetime)

    def test_boundary_order_lands_on_the_next_bahrain_day(self):
        """21:00 UTC is midnight in Bahrain: the marker is what lets the browser
        place this order on the 28th rather than the 27th."""
        payload = json.loads(_order(datetime(2026, 8, 27, 21, 0, 0)).model_dump_json())
        self.assertEqual(payload["created_at"], "2026-08-27T21:00:00Z")
        self.assertEqual(as_bahrain(datetime(2026, 8, 27, 21, 0)).date().isoformat(), "2026-08-28")

class NoUntaggedDatetimeTestCase(unittest.TestCase):
    """Guard against a new display field being added without the UTC marker.

    A plain ``datetime`` field serializes with ``"format": "date-time"`` in the
    serialization JSON schema; a ``UtcDateTime`` is rewritten to a plain string by
    the ``PlainSerializer``, so the format key disappears. That makes the schema a
    reliable detector without having to build an instance of every model.
    """

    def _date_time_formats(self, schema, path="") -> list[str]:
        found = []
        if isinstance(schema, dict):
            if schema.get("format") == "date-time":
                found.append(path)
            for key, value in schema.items():
                if key in ("properties", "$defs"):
                    for name, sub in value.items():
                        found += self._date_time_formats(sub, f"{path}.{name}" if path else name)
                elif isinstance(value, (dict, list)):
                    found += self._date_time_formats(value, path)
        elif isinstance(schema, list):
            for item in schema:
                found += self._date_time_formats(item, path)
        return found

    def test_no_display_output_schema_leaks_an_untagged_datetime(self):
        from app.schemas import auth, dashboard, menu, orders, settings, store

        offenders = []
        for module in (auth, dashboard, menu, orders, settings, store):
            for name in sorted(dir(module)):
                model = getattr(module, name)
                if not (isinstance(model, type) and hasattr(model, "model_json_schema")):
                    continue
                if not name.endswith("Out"):
                    continue
                schema = model.model_json_schema(mode="serialization")
                for field_path in self._date_time_formats(schema):
                    offenders.append(f"{module.__name__}.{name}.{field_path}")

        self.assertEqual(offenders, [], f"untagged datetime fields: {offenders}")

    def test_the_detector_actually_catches_an_untagged_field(self):
        """Sanity-check the guard: the device sync schema is deliberately left
        untagged (its Flutter client owns that protocol), so it must trip."""
        from app.schemas.sync import SyncCatalogOut

        schema = SyncCatalogOut.model_json_schema(mode="serialization")
        self.assertIn("generated_at", self._date_time_formats(schema))


if __name__ == "__main__":
    unittest.main()
