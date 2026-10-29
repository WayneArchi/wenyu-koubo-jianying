"""Synthetic risk checks; no audio listening or native-app quality claims."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_plan import audit


def plan(text="保留完整词组", end=2000000, word_end=1700000):
    return {"sources": [{"id": "a", "duration_us": 10000000}],
            "approved": True, "approval_reference": "Synthetic test only",
            "speaker_identity_confirmed": True, "full_listening_review": False,
            "clips": [{"source_id": "a", "source_start_us": 0, "source_end_us": end,
                       "target_start_us": 0, "speaker_status": "confirmed_target",
                       "word_intervals": [{"text": text, "start_us": 100000,
                                           "end_us": word_end}]}]}


class SpeechContinuityTests(unittest.TestCase):
    def test_complete_phrase_with_tail_is_not_fragment(self):
        result = audit(plan())
        self.assertTrue(result["ready_for_native_edit"])
        self.assertEqual(result["continuity_risks"], [])
        self.assertFalse(result["listening_claim_received"])

    def test_single_character_fragment_blocks_even_with_global_listening_claim(self):
        p = plan("会", 433333, 390000)
        p["full_listening_review"] = True
        result = audit(p)
        self.assertTrue(result["valid_structure"])
        self.assertFalse(result["ready_for_native_edit"])
        self.assertIn("isolated_single_character", result["continuity_risks"][0]["reasons"])

    def test_natural_short_reply_requires_local_evidence_and_independence(self):
        p = plan("对", 450000, 300000)
        review = {"listened": True, "reason": "Synthetic independent reply claim"}
        p["clips"][0]["continuity_review"] = review
        self.assertFalse(audit(p)["ready_for_native_edit"])
        review["independent_utterance"] = True
        result = audit(p)
        self.assertTrue(result["ready_for_native_edit"])
        self.assertTrue(result["continuity_risks"][0]["review_claim_received"])

    def test_short_multi_character_clip_is_reviewed_too(self):
        result = audit(plan("不是", 450000, 300000))
        self.assertFalse(result["ready_for_native_edit"])
        self.assertIn("short_speech_fragment", result["continuity_risks"][0]["reasons"])

    def test_tight_final_tail_is_not_missed(self):
        result = audit(plan(word_end=1990000))
        self.assertFalse(result["ready_for_native_edit"])
        self.assertEqual(result["continuity_risks"][0]["reasons"], ["tight_tail_candidate"])

    def test_source_contiguous_boundary_has_no_artificial_tail_requirement(self):
        p = plan(word_end=1990000)
        p["clips"].append({"source_id": "a", "source_start_us": 2000000,
                           "source_end_us": 4000000, "target_start_us": 2000000,
                           "speaker_status": "confirmed_target",
                           "word_intervals": [{"text": "继续完整原话", "start_us": 2010000,
                                               "end_us": 3700000}]})
        self.assertTrue(audit(p)["ready_for_native_edit"])

    def test_timestamp_mismatch_still_fails_instead_of_using_review_override(self):
        p = plan(word_end=2100000)
        p["clips"][0]["continuity_review"] = {"listened": True, "reason": "Synthetic claim"}
        self.assertFalse(audit(p)["valid_structure"])


if __name__ == "__main__":
    unittest.main()
