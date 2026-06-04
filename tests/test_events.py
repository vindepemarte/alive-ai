import asyncio
import unittest

from core.events import AuditOptions, HistoryOptions, NervousEvent, NervousSystem


class NervousSystemEventTests(unittest.TestCase):
    def test_legacy_listener_gets_payload_and_envelope_listener_gets_event(self):
        nervous = NervousSystem()
        seen_payload = []
        seen_event = []

        nervous.on("message_received", lambda data: seen_payload.append(data))
        nervous.on("message_received", lambda event: seen_event.append(event), envelope=True)

        emitted = asyncio.run(nervous.emit("message_received", {"text": "hey"}))

        self.assertEqual(seen_payload, [{"text": "hey"}])
        self.assertIsInstance(seen_event[0], NervousEvent)
        self.assertEqual(seen_event[0].payload["text"], "hey")
        self.assertIs(emitted, seen_event[0])

    def test_async_sync_and_coroutine_returning_listeners_work(self):
        nervous = NervousSystem()
        order = []

        async def async_cb(_data):
            order.append("async")

        def sync_cb(_data):
            order.append("sync")

        def returns_coroutine(_data):
            async def inner():
                order.append("returned")

            return inner()

        nervous.on("tick", async_cb)
        nervous.on("tick", sync_cb)
        nervous.on("tick", returns_coroutine)

        asyncio.run(nervous.emit("tick", {}))

        self.assertEqual(order, ["async", "sync", "returned"])

    def test_listener_exception_does_not_stop_dispatch(self):
        nervous = NervousSystem()
        seen = []

        def bad(_data):
            raise RuntimeError("boom")

        nervous.on("x", bad)
        nervous.on("x", lambda data: seen.append(data))

        asyncio.run(nervous.emit("x", {"ok": True}))

        self.assertEqual(seen, [{"ok": True}])

    def test_history_and_audit_are_opt_in_and_redacted(self):
        nervous = NervousSystem()

        asyncio.run(nervous.emit("private", {"text": "secret"}))
        self.assertEqual(nervous.recent(), [])
        self.assertEqual(nervous.audit_log(), [])

        asyncio.run(nervous.emit(
            "private",
            {"text": "secret", "safe": "ok"},
            history=HistoryOptions(record=True, include_payload=False),
            audit=AuditOptions(record=True, include_payload=True),
        ))

        self.assertEqual(nervous.recent("private")[0].payload, {})
        self.assertEqual(nervous.audit_log()[0]["payload"]["text"], "[redacted]")
        self.assertEqual(nervous.audit_log()[0]["payload"]["safe"], "ok")

    def test_audit_redacts_common_secret_keys_case_insensitively_and_limit_zero_is_empty(self):
        nervous = NervousSystem()

        asyncio.run(nervous.emit(
            "private",
            {"api_key": "a", "token": "b", "Password": "c", "nested": {"Authorization": "d"}},
            history=HistoryOptions(record=True, include_payload=True),
            audit=AuditOptions(record=True, include_payload=True),
        ))

        payload = nervous.audit_log()[0]["payload"]
        self.assertEqual(payload["api_key"], "[redacted]")
        self.assertEqual(payload["token"], "[redacted]")
        self.assertEqual(payload["Password"], "[redacted]")
        self.assertEqual(payload["nested"]["Authorization"], "[redacted]")
        self.assertEqual(nervous.recent(limit=0), [])
        self.assertEqual(nervous.audit_log(limit=0), [])


if __name__ == "__main__":
    unittest.main()
