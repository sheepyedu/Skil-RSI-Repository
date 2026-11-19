"""CPU audit of real completed trials, projection protection and judge retry classification."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from audit_workbuddy import audit_trial, clm_edit_ledger, judge_quality, load, projection_proof, sha
from clm.context import digest, encode


def main(base, run, output):
    roots = sorted(base.glob("formal-[0-9][0-9]")) + sorted(base.glob("pilot-[0-9][0-9]"))
    if (base / "capacity-probe").exists():
        roots.append(base / "capacity-probe")
    edits, checked = clm_edit_ledger(roots)
    assert edits and checked
    event = next(e for e in edits if e["edit"] == "accepted")
    source = Path(event["evidence"])
    checks = ["all recorded CLM projections independently reconstructed from captured inputs"]
    with tempfile.TemporaryDirectory(prefix="wb-postprocess-check-") as temporary:
        root = Path(temporary)
        target = root / "case/wire/00001/receipt.json"
        target.parent.mkdir(parents=True)
        for name in ("request.raw.json", "request.sent.json", "receipt.json"):
            shutil.copyfile(source.parent / name, target.parent / name)
        wire = load(target)
        projection_proof(target, wire)
        payload = load(target.parent / "request.sent.json")
        # Update every checksum to ensure the check rejects protected-content alteration,
        # rather than merely noticing a stale digest.
        payload["input"][0]["content"] = "altered protected instruction"
        (target.parent / "request.sent.json").write_bytes(encode(payload))
        wire["sent_sha256"] = sha(target.parent / "request.sent.json")
        wire["clm"]["upstream_input_sha256"] = digest(payload["input"])
        wire["clm"]["after_input_bytes"] = len(encode(payload["input"]))
        try:
            projection_proof(target, wire)
        except ValueError:
            pass
        else:
            raise AssertionError("Protected instruction mutation was accepted")
        checks.append("reject changed protected text even with recomputed checksums")
        (root / "verifier").mkdir()
        item = {"id": "judge-fixture", "status": "pass", "judge_meta": {
            "judge_path": "llm", "llm_retry_error": "RemoteDisconnected", "fallback_mode": "none",
            "verdict_parse_strategy": "json", "raw_response_excerpt": '{"verdict":"pass"}',
            "raw_response_chars": len('{"verdict":"pass"}')}}
        score = root / "verifier/score.json"
        score.write_text(json.dumps(item))
        quality = judge_quality(root, {})
        assert not quality["requires_review"] and len(quality["recovered_retry_findings"]) == 1
        item["judge_meta"].update(raw_response_excerpt="", raw_response_chars=0)
        score.write_text(json.dumps(item))
        assert judge_quality(root, {})["requires_review"]
        checks.append("distinguish a recovered retry from an empty final judge response")
        item["judge_meta"].update(llm_retry_error="", raw_response_excerpt='{"verdict":"pass"}',
                                  raw_response_chars=len('{"verdict":"pass"}'), image_input_error="fixture failure")
        score.write_text(json.dumps(item))
        assert judge_quality(root, {})["requires_review"]
        checks.append("flag image-input failures despite a parsed textual verdict")
        agent_item = {"id": "agent-fixture", "judge_type": "agent", "status": "fail",
                      "source": "static", "judge_meta": {}}
        score.write_text(json.dumps(agent_item))
        assert judge_quality(root, {})["requires_review"]
        agent_item.update(status="pass", source="agent_judge", judge_meta={
            "judge": "agent_judge", "agent_returncode": 0, "model": "gpt-6.1-sol"})
        score.write_text(json.dumps(agent_item))
        assert judge_quality(root, {})["requires_review"]
        agent_log = root / "verifier/agent-judge/agent-fixture.json"
        agent_log.parent.mkdir()
        agent_log.write_text(json.dumps({"verdict": "pass", "agent_returncode": 0, "model": "gpt-6.1-sol"}))
        agent_stream = agent_log.with_suffix(".stream.log")
        agent_stream.write_text(json.dumps({"type": "result", "subtype": "success", "is_error": False}) + "\n")
        assert not judge_quality(root, {})["requires_review"]
        agent_log.write_text(json.dumps({"verdict": "fail", "agent_returncode": 0, "model": "gpt-6.1-sol"}))
        assert judge_quality(root, {})["requires_review"]
        agent_item["status"] = "fail"
        score.write_text(json.dumps(agent_item))
        assert not judge_quality(root, {})["requires_review"]
        agent_stream.write_text(json.dumps({"type": "result", "subtype": "error_during_execution", "is_error": True}) + "\n")
        assert judge_quality(root, {})["requires_review"]
        checks.append("reject missing, unsubmitted and inconsistent interactive verdicts despite stage exit zero")
        checks.append("reject CBC error terminal masked by a successful tee pipeline")
        score.write_text(json.dumps({"judges": [{"ok": True, "metadata": {
            "script_exit_code": 0, "raw": {"failed_checks": [{
                "name": "score_eval_core_failed", "group": "scorer",
                "detail": "AttributeError: list has no attribute values"}]}}}]}))
        assert judge_quality(root, {})["requires_review"]
        score.write_text(json.dumps({"failed_checks": [{"name": "artifact_refs_consistent",
            "group": "evidence_export_refs", "detail": "wrong JSON type"}]}))
        assert not judge_quality(root, {})["requires_review"]
        checks.append("flag deterministic evaluator crashes masked by exit zero, preserve ordinary rubric failures")
        normalized = {"judge_name": "rule", "judge_type": "rule_script", "ok": False,
                      "status": "build_error", "errors": [], "metadata": {"script_exit_code": 0}}
        score.write_text(json.dumps({"judges": [normalized]}))
        assert judge_quality(root, {})["requires_review"]
        normalized.update(ok=True, status="fail")
        score.write_text(json.dumps({"judges": [normalized]}))
        assert not judge_quality(root, {})["requires_review"]
        normalized.update(ok=False, status="judge_error")
        score.write_text(json.dumps({"judges": [normalized]}))
        assert judge_quality(root, {})["requires_review"]
        checks.append("flag normalized official build/judge errors even with empty errors and wrapper exit zero")
    once, once_count = clm_edit_ledger([source.parent.parent.parent])
    twice, twice_count = clm_edit_ledger([source.parent.parent.parent] * 2)
    assert once == twice and once_count == twice_count
    checks.append("copied wire prefixes are counted exactly once")
    progress = [r for r in load(run / "progress.json") if r.get("accepted")]
    audited, threads = [], {}
    for receipt in progress:
        arm = receipt["arm"]
        proof = audit_trial(run, receipt["row"], arm, threads.get(arm))
        threads[arm] = proof["thread"]
        audited.append({"position": receipt["row"]["position"], "arm": arm, **proof})
    result = {"scope": "Running-stage CPU diagnostic; not the final 65-pair delivery audit",
              "model_api_calls": 0, "projection_requests_verified": checked, "edit_events": edits,
              "checks": checks, "trials": audited, "trials_audited": len(audited),
              "judge_technical_reviews_needed": sum(x["judge_quality"]["requires_review"] for x in audited),
              "postprocessor_sha256": sha(Path(__file__).with_name("audit_workbuddy.py"))}
    with output.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("trials", "edit_events")}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.base, args.run, args.output)
