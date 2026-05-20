import time
import unittest

from project_utils.data_cache import TTLCache, get_cache


class TestTTLCache(unittest.TestCase):
    def test_set_and_get(self):
        cache = TTLCache(default_ttl=60.0)
        cache.set('a', [1, 2])
        self.assertEqual(cache.get('a'), [1, 2])

    def test_expires(self):
        cache = TTLCache(default_ttl=0.05)
        cache.set('k', 'v')
        time.sleep(0.08)
        self.assertIsNone(cache.get('k'))

    def test_get_or_fetch_uses_cache(self):
        cache = TTLCache(default_ttl=60.0)
        calls = []

        def fetch():
            calls.append(1)
            return 42

        v1, hit1 = cache.get_or_fetch('x', fetch)
        v2, hit2 = cache.get_or_fetch('x', fetch)
        self.assertEqual(v1, 42)
        self.assertEqual(v2, 42)
        self.assertFalse(hit1)
        self.assertTrue(hit2)
        self.assertEqual(len(calls), 1)

    def test_force_refetch(self):
        cache = TTLCache(default_ttl=60.0)
        cache.set('n', 1)
        v, hit = cache.get_or_fetch('n', lambda: 2, force=True)
        self.assertEqual(v, 2)
        self.assertFalse(hit)

    def test_named_cache_singleton(self):
        self.assertIs(get_cache('test_ns'), get_cache('test_ns'))


if __name__ == '__main__':
    unittest.main()
