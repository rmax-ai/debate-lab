"""Tests for the evidence extractor."""

from debate_evidence.extractor import EvidenceExtractor


class TestEvidenceExtractor:
    async def test_extract_web_search_results(self):
        extractor = EvidenceExtractor()
        tool_result = {
            "source_type": "web_search",
            "results": [
                {"title": "T1", "url": "http://a", "snippet": "S1", "reliability_score": 0.8},
                {"title": "T2", "url": "http://b", "snippet": "S2"},
            ],
        }
        refs = await extractor.extract(tool_result, retrieved_by="advocate")
        assert len(refs) == 2
        assert refs[0].id == "E-01"
        assert refs[0].title == "T1"
        assert refs[0].reliability_score == 0.8
        assert refs[0].retrieved_by == "advocate"
        assert refs[1].id == "E-02"

    async def test_extract_empty_results(self):
        extractor = EvidenceExtractor()
        refs = await extractor.extract(
            {"source_type": "web_search", "results": []},
            retrieved_by="agent",
        )
        assert refs == []

    async def test_extract_dict_result(self):
        extractor = EvidenceExtractor()
        refs = await extractor.extract(
            {"source_type": "doc_search", "results": {"title": "Doc", "content": "body"}},
            retrieved_by="agent",
        )
        assert len(refs) == 1
        assert refs[0].source_type == "doc_search"

    async def test_counter_persists_across_extracts(self):
        extractor = EvidenceExtractor(ref_counter=5)
        refs1 = await extractor.extract(
            {"results": [{"title": "A", "snippet": "a"}]},
            retrieved_by="a",
        )
        refs2 = await extractor.extract(
            {"results": [{"title": "B", "snippet": "b"}]},
            retrieved_by="b",
        )
        assert refs1[0].id == "E-06"
        assert refs2[0].id == "E-07"

    async def test_reset_counter(self):
        extractor = EvidenceExtractor(ref_counter=10)
        await extractor.extract({"results": [{"title": "X", "snippet": "x"}]}, retrieved_by="a")
        extractor.reset_counter()
        refs = await extractor.extract(
            {"results": [{"title": "Y", "snippet": "y"}]},
            retrieved_by="b",
        )
        assert refs[0].id == "E-01"
