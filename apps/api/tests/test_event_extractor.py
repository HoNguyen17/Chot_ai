"""Lượt 2 (SPEC M3 §3.3): prompt chỉ chứa đoạn + ngữ cảnh CHỈ ĐỌC + bản đồ chủ đề."""

import json

from chot.adapters.llm.event_extractor import EXTRACTION_SCHEMA, LLMEventExtractor
from chot.adapters.llm.topic_mapper import LLMTopicMapper
from chot.domain.chunking import Chunk
from chot.domain.models import Participant, Thread, Transcript, Utterance


class FakeClient:
    def __init__(self, reply: dict) -> None:
        self.reply, self.prompts = reply, []

    def complete_json(self, prompt, schema):
        self.prompts.append(prompt)
        return json.dumps(self.reply)


TR = Transcript(
    meeting_id="x",
    participants=[Participant(name="Bách", is_chair=True), Participant(name="Hạnh")],
    utterances=[
        Utterance(id=f"u{i:03d}", index=i, ts=i, speaker="Hạnh", text=f"câu số {i}")
        for i in range(1, 8)
    ],
)
MAP = [Thread(id="tet-shipping", title="Vận chuyển Tết", keys=["đường biển"], utt_ids=["u002"])]


def test_chunk_prompt_marks_context_read_only_and_hides_other_utterances():
    client = FakeClient({"threads": [], "events": []})
    LLMEventExtractor(client).extract_chunk(
        TR, MAP, Chunk(label_ids=["u004", "u005"], context_ids=["u003"])
    )
    prompt = client.prompts[0]
    assert "[CHỈ ĐỌC] u003" in prompt
    assert "\nu004 " in prompt and "\nu005 " in prompt
    assert "u002 [" not in prompt and "u006" not in prompt
    assert "tet-shipping" in prompt and "đường biển" in prompt


def test_single_call_prompt_has_no_topic_map():
    client = FakeClient({"threads": [], "events": []})
    LLMEventExtractor(client).extract(TR)
    assert "Không có bản đồ" in client.prompts[0]
    assert "[CHỈ ĐỌC] u0" not in client.prompts[0]
    assert all(f"\nu00{i} " in client.prompts[0] for i in range(1, 8))
    assert "{{" not in client.prompts[0]


def test_schema_asks_for_durable_hint_and_new_key():
    required = EXTRACTION_SCHEMA["properties"]["events"]["items"]["required"]
    assert {"durable_hint", "new_key"} <= set(required)


def test_topic_mapper_returns_threads_with_keys_and_utts():
    reply = {"threads": [{"id": "a", "title": "A", "keys": ["k"], "utt_ids": ["u001"]}]}
    client = FakeClient(reply)
    threads = LLMTopicMapper(client).map(TR)
    assert threads == [Thread(id="a", title="A", keys=["k"], utt_ids=["u001"])]
    assert "u007" in client.prompts[0] and "{{" not in client.prompts[0]
