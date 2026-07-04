"""Tests for the mock web search."""

from debate_tools.web_search import MockWebSearch


class TestMockWebSearch:
    async def test_execute_returns_results(self):
        search = MockWebSearch()
        result = await search.execute({"query": "event bus architecture"})
        assert result["query"] == "event bus architecture"
        assert len(result["results"]) > 0
        assert "title" in result["results"][0]
        assert "snippet" in result["results"][0]
        assert "url" in result["results"][0]

    async def test_respects_limit(self):
        search = MockWebSearch()
        result = await search.execute({"query": "test", "limit": 2})
        assert len(result["results"]) == 2

    async def test_increments_call_count(self):
        search = MockWebSearch()
        assert search.call_count == 0
        await search.execute({"query": "q1"})
        await search.execute({"query": "q2"})
        assert search.call_count == 2
        assert len(search.call_history) == 2

    async def test_call_history_tracks_queries(self):
        search = MockWebSearch()
        await search.execute({"query": "specific query text"})
        assert search.call_history[0]["query"] == "specific query text"
        assert search.call_history[0]["call"] == 1

    async def test_custom_results(self):
        custom = [{"title": "Custom", "url": "http://c", "snippet": "Custom result"}]
        search = MockWebSearch(results=custom)
        result = await search.execute({"query": "test"})
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Custom"
        assert result["total_results"] == 1
