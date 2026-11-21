from unittest import mock

from django.test import SimpleTestCase

from apps.cases.analysis import find_issues
from apps.cases.extract import Fact


def fact(i, page):
    return Fact(id=f"F{i}", type="statement", page=page, date="", time="", source="", summary="s", quote="q",
                verified=True, verified_page=page)


class FindIssuesTests(SimpleTestCase):
    def test_two_calls_are_merged_and_invalid_ids_dropped(self):
        facts = [fact(1, 3), fact(2, 7), fact(3, 9)]
        item = lambda ids: {"topic": "t", "fact_ids": ids, "explanation": "e", "importance": "high"}

        def chat_json(system, user, schema, **kw):
            self.assertEqual(kw["max_tokens"], 16000)
            if "contradictions" in schema["properties"]:
                return {"contradictions": [item(["F1", "F2", "F99"]), item(["F3"])], "summary": "xulosa"}
            return {"procedural_issues": [item(["F3"]), item(["F98"])], "summary": ""}

        llm = mock.Mock(chat_json=mock.Mock(side_effect=chat_json))
        with mock.patch("apps.cases.analysis.get_llm", return_value=llm):
            findings, summary = find_issues(facts, model="m")
        self.assertEqual(llm.chat_json.call_count, 2)
        self.assertEqual(summary, "xulosa")
        self.assertEqual([(f.kind, f.fact_ids, f.pages) for f in findings],
                         [("contradiction", ["F1", "F2"], [3, 7]), ("procedural", ["F3"], [9])])
        self.assertEqual(findings[0].dropped_ids, ["F99"])
