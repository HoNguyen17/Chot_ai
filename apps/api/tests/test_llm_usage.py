"""Client LLM cộng dồn token để tính chi phí mỗi lần eval (giả lập ở biên SDK OpenAI)."""

from types import SimpleNamespace as NS

from chot.adapters.llm.client import OpenAICompatibleClient


class _FakeCompletions:
    def create(self, **_):
        return NS(
            choices=[NS(message=NS(content="{}"))],
            usage=NS(prompt_tokens=1000, completion_tokens=200),
        )


def test_client_accumulates_usage_across_calls():
    client = OpenAICompatibleClient(model="m", api_key="k")
    client._client = NS(chat=NS(completions=_FakeCompletions()))
    client.complete_json("a", None)
    client.complete_json("b", None)
    assert client.usage == {"calls": 2, "prompt_tokens": 2000, "completion_tokens": 400}
