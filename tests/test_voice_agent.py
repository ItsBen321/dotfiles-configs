"""Lifecycle and cache tests. Fake Codex emits events without operating a PC."""

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "hypr/.local/bin/voice-agent"
loader = importlib.machinery.SourceFileLoader("voice_agent", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
agent = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = agent
loader.exec_module(agent)


FAKE_CODEX = '''#!/usr/bin/env python3
import json, os, subprocess, sys, time
payload = json.load(sys.stdin)
def emit(value):
    print(json.dumps(value), flush=True)
if os.environ.get("FAKE_CHILD_PID"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    open(os.environ["FAKE_CHILD_PID"], "w").write(str(child.pid))
if os.environ.get("FAKE_HANG"):
    time.sleep(60)
if os.environ.get("FAKE_EXIT"):
    sys.exit(1)
if "evidence" in payload:
    final = {"entries": [{"key": "steam:deadlock", "fact": "Deadlock's Steam app ID is 1422450.", "evidence_id": 0}]}
else:
    command = "steam -applaunch 1422450"
    emit({"type": "item.started", "item": {"type": "command_execution", "command": command}})
    emit({"type": "item.completed", "item": {"type": "command_execution", "command": command,
          "exit_code": 0, "aggregated_output": "Deadlock window visible"}})
    final = {"status": "completed", "summary": "Deadlock's window is visible.", "invalid_memory_keys": []}
emit({"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(final)}})
emit({"type": "turn.completed"})
'''


class VoiceAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = agent.Paths(self.root / "runtime", self.root / "state",
                                 self.root / "config/config.toml", self.root / "overlay")
        self.paths.prepare()
        self.config = dict(agent.DEFAULTS)
        fake = self.root / "codex"
        fake.write_text(FAKE_CODEX)
        fake.chmod(0o700)
        self.config["codex_bin"] = str(fake)
        agent.STOP = False
        self.visual = patch.object(agent, "visual").start()
        self.addCleanup(patch.stopall)
        self.env = patch.dict(os.environ, {"FAKE_HANG": "", "FAKE_EXIT": "", "FAKE_CHILD_PID": ""})
        self.env.start()

    def memory(self, entries, **extra):
        data = {"version": 1, "host": agent.host_id(), "generation": 0,
                "entries": entries, **extra}
        agent.atomic_json(self.paths.state / "memory.json", data)
        return data

    def entry(self, key="app:firefox", fact="Firefox uses /usr/bin/firefox", command="command -v firefox", **extra):
        return {"key": key, "fact": fact, "command": command,
                "verified_at": time.time(), **extra}

    def job(self, **extra):
        return {"request": "Launch Deadlock", "result": {"status": "completed",
                "summary": "Deadlock's window is visible.", "invalid_memory_keys": []},
                "generation": 0, "known_keys": [], "failed_commands": [],
                "evidence": [{"command": "steam -applaunch 1422450", "output": "Deadlock window visible"}], **extra}

    def test_cache_selection_has_relevance_and_a_hard_prompt_budget(self):
        data = self.memory([self.entry(), self.entry("steam:deadlock", "Deadlock Steam ID 1422450")])
        selected = agent.relevant_memory(data, "launch the deadlock game", 1000)
        self.assertEqual([e["key"] for e in selected], ["steam:deadlock"])
        self.assertEqual(agent.relevant_memory(data, "Firefox", 5), [])

    def test_cache_expiration_corruption_and_machine_change_fail_open(self):
        self.memory([self.entry(), self.entry("old:app", verified_at=time.time() - 31 * 86400),
                     self.entry("future:app", verified_at=time.time() + 3600), {"bad": "entry"}])
        self.assertEqual(len(agent.load_memory(self.paths, self.config)["entries"]), 1)
        self.memory([self.entry()], host="another-machine")
        self.assertEqual(agent.load_memory(self.paths, self.config)["entries"], [])
        (self.paths.state / "memory.json").write_text("{broken")
        self.assertEqual(agent.load_memory(self.paths, self.config)["entries"], [])

    def test_learning_requires_evidence_and_rejects_secret_patterns(self):
        job = self.job()
        agent.merge_memory(self.paths, self.config, job, [
            {"key": "steam:deadlock", "fact": "Deadlock Steam ID 1422450", "evidence_id": 0},
            {"key": "app:invented", "fact": "Invented", "evidence_id": 9},
            {"key": "bad:secret", "fact": "api_key=private-value", "evidence_id": 0},
            {"key": "bad:bool", "fact": "Invented", "evidence_id": True},
        ])
        data = agent.load_memory(self.paths, self.config)
        self.assertEqual([e["key"] for e in data["entries"]], ["steam:deadlock"])
        self.assertEqual((self.paths.state / "memory.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.paths.state.stat().st_mode & 0o777, 0o700)

    def test_clear_generation_prevents_old_worker_from_restoring_cache(self):
        self.memory([], generation=1)
        agent.merge_memory(self.paths, self.config, self.job(), [
            {"key": "steam:deadlock", "fact": "ID 1422450", "evidence_id": 0}])
        self.assertEqual(agent.load_memory(self.paths, self.config)["entries"], [])

    def test_failed_commands_and_explicit_stale_keys_are_removed(self):
        self.memory([self.entry(), self.entry("steam:deadlock", "ID 1422450", "steam -applaunch 1422450"),
                     self.entry("app:keep", "Unrelated", "other")])
        job = self.job(known_keys=["app:firefox"], failed_commands=["steam -applaunch 1422450"])
        job["result"]["invalid_memory_keys"] = ["app:firefox", "app:keep"]
        agent.merge_memory(self.paths, self.config, job, [])
        entries = agent.load_memory(self.paths, self.config)["entries"]
        self.assertEqual([e["key"] for e in entries if e.get("kind") != "failed_approach"], ["app:keep"])
        self.assertEqual(len([e for e in entries if e.get("kind") == "failed_approach"]), 1)

    def test_failed_approach_is_available_to_future_requests_with_context(self):
        failure = {"command": "mpv missing.mp4", "exit_code": 2, "output": "Cannot open file"}
        job = self.job(failed_commands=[failure])
        agent.merge_memory(self.paths, self.config, job, [])
        hints = agent.relevant_memory(agent.load_memory(self.paths, self.config), "Launch Deadlock", 5000)
        self.assertEqual(hints[0]["kind"], "failed_approach")
        self.assertEqual(hints[0]["failed_command"], failure["command"])
        self.assertIn("Cannot open file", hints[0]["fact"])
        self.assertIn("does not prove every subcommand failed", hints[0]["fact"])

    def test_background_launch_exit_zero_is_not_enough_to_learn_a_working_method(self):
        job = self.job(evidence=[{"command": "mpv example.mp4 &", "output": ""}])
        agent.merge_memory(self.paths, self.config, job, [
            {"key": "app:mpv", "fact": "Background mpv works", "evidence_id": 0}])
        self.assertEqual(agent.load_memory(self.paths, self.config)["entries"], [])

    def test_failures_survive_interruption_of_the_optional_learning_model(self):
        path = self.paths.runtime / "job.json"
        agent.atomic_json(path, self.job(failed_commands=[{
            "command": "mpv missing.mp4", "exit_code": 2, "output": "Cannot open file"}]))
        with patch.object(agent.os, "nice"), patch.object(agent, "run_codex", side_effect=InterruptedError):
            agent.learn(self.paths, self.config, path)
        entries = agent.load_memory(self.paths, self.config)["entries"]
        self.assertEqual(entries[0]["kind"], "failed_approach")

    def test_result_is_reported_before_background_learning_is_started(self):
        order = []
        with patch.object(agent, "report", side_effect=lambda *_: order.append("report")), \
                patch.object(agent, "start_learning", side_effect=lambda *_: order.append("learn")):
            status = agent.run_task(self.paths, self.config, "Launch Deadlock")
        self.assertEqual(status, 0)
        self.assertEqual(order, ["report", "learn"])
        self.assertFalse(agent.active(self.paths.runtime / "task.active.json"))

    def test_background_pass_persists_facts_without_repeating_commands(self):
        job_path = self.paths.runtime / "job.json"
        agent.atomic_json(job_path, self.job())
        # Do not change the test runner's scheduling priority.
        with patch.object(agent.os, "nice"):
            agent.learn(self.paths, self.config, job_path)
        entries = agent.load_memory(self.paths, self.config)["entries"]
        self.assertEqual(entries[0]["key"], "steam:deadlock")
        self.assertFalse(job_path.exists())
        command = agent.codex_command(self.paths, self.config, True)
        self.assertIn("read-only", command)
        self.assertIn("shell_tool", command)
        self.assertNotIn("--approve-for-me", command)

    def test_already_known_commands_do_not_spend_another_learning_call(self):
        self.memory([self.entry("steam:deadlock", "ID 1422450", "steam -applaunch 1422450")])
        job_path = self.paths.runtime / "job.json"
        agent.atomic_json(job_path, self.job())
        with patch.object(agent.os, "nice"), patch.object(agent, "run_codex") as execute:
            agent.learn(self.paths, self.config, job_path)
        execute.assert_not_called()

    def test_a_new_task_preempts_learning_and_no_failed_result_is_learned(self):
        order = []
        with patch.object(agent, "stop_active", side_effect=lambda *_: order.append("stop")), \
                patch.object(agent, "run_codex", side_effect=ValueError("failed")), \
                patch.object(agent, "report", side_effect=lambda *_: order.append("report")), \
                patch.object(agent, "start_learning") as learn:
            self.assertEqual(agent.run_task(self.paths, self.config, "Launch Deadlock"), 1)
        self.assertEqual(order, ["stop", "report"])
        learn.assert_not_called()

    def test_memory_worker_skips_when_a_foreground_task_is_running(self):
        path = self.paths.runtime / "job.json"
        agent.atomic_json(path, self.job())
        with agent.task_lock(self.paths, "task"), patch.object(agent.os, "nice"), \
                patch.object(agent, "run_codex") as execute:
            agent.learn(self.paths, self.config, path)
        execute.assert_not_called()

    def test_timeout_stops_the_entire_process_group(self):
        self.config["task_timeout_seconds"] = 0.3
        child_file = self.root / "child.pid"
        with patch.dict(os.environ, {"FAKE_HANG": "1", "FAKE_CHILD_PID": str(child_file)}):
            with self.assertRaises(TimeoutError):
                agent.run_codex(self.paths, self.config, {"request": "do nothing"})
        pid = int(child_file.read_text())
        # A killed orphan can briefly remain as a zombie awaiting PID 1.
        stat = Path(f"/proc/{pid}/stat")
        for _ in range(20):
            if not stat.exists() or stat.read_text().rsplit(")", 1)[1].split()[0] == "Z":
                break
            time.sleep(0.05)
        else:
            self.fail("Child survived the timeout")

    def test_stale_pid_marker_does_not_signal_a_reused_pid(self):
        marker = self.paths.runtime / "task.active.json"
        agent.atomic_json(marker, {"pid": os.getpid(), "start": "wrong-start-time"})
        with patch.object(agent.os, "kill") as kill:
            self.assertFalse(agent.stop_active(marker))
        kill.assert_not_called()

    def test_cancellation_interrupts_a_running_codex_process(self):
        def cancel():
            agent.STOP = True
        timer = threading.Timer(0.15, cancel)
        with patch.dict(os.environ, {"FAKE_HANG": "1"}):
            timer.start()
            try:
                with self.assertRaises(InterruptedError):
                    agent.run_codex(self.paths, self.config, {"request": "do nothing"})
            finally:
                timer.cancel()

    def test_confirmation_is_bound_to_one_recent_proposal(self):
        pending = self.paths.runtime / "confirmation.json"
        agent.atomic_json(pending, {"host": agent.host_id(), "created_at": time.time(),
                                   "request": "Delete the selected file", "proposal": "Delete /tmp/example"})
        final = {"status": "completed", "summary": "Deleted the file", "invalid_memory_keys": []}
        with patch.object(agent, "report"), patch.object(agent, "start_learning"), \
                patch.object(agent, "run_codex", return_value=(final, [], [])) as execute:
            agent.run_task(self.paths, self.config, "", confirm=True)
        payload = execute.call_args.args[2]
        self.assertEqual(payload["confirmation"], {"approved_action": "Delete /tmp/example"})
        self.assertFalse(pending.exists())
        with self.assertRaises(ValueError):
            agent.run_task(self.paths, self.config, "", confirm=True)

    def test_expired_confirmation_is_rejected(self):
        agent.atomic_json(self.paths.runtime / "confirmation.json", {
            "host": agent.host_id(), "created_at": time.time() - 121,
            "request": "Delete a file", "proposal": "Delete /tmp/example"})
        with self.assertRaises(ValueError), patch.object(agent, "run_codex") as execute:
            agent.run_task(self.paths, self.config, "", confirm=True)
        execute.assert_not_called()

    def test_concurrent_task_is_rejected_by_the_lock(self):
        with agent.task_lock(self.paths, "task"):
            self.assertTrue(agent.active(self.paths.runtime / "task.active.json"))
            with self.assertRaises(BlockingIOError):
                with agent.task_lock(self.paths, "task"):
                    self.fail("Second task acquired the lock")

    def test_request_is_data_and_command_flags_never_bypass_the_sandbox(self):
        command = agent.codex_command(self.paths, self.config, False)
        self.assertEqual(command[-1], "-")
        self.assertIn("--approve-for-me", command)
        self.assertIn("--ignore-user-config", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        self.assertNotIn("danger-full-access", command)

    def test_fast_tier_is_explicit_and_separate_from_reasoning_and_learning(self):
        self.assertNotIn('service_tier="fast"', agent.codex_command(self.paths, self.config, False))
        self.config["fast_mode"] = True
        self.assertIn('service_tier="fast"', agent.codex_command(self.paths, self.config, False))
        self.assertNotIn('service_tier="fast"', agent.codex_command(self.paths, self.config, True))

    def test_timing_log_distinguishes_events_and_command_durations(self):
        agent.run_codex(self.paths, self.config, {"request": "Launch Deadlock"})
        timing = agent.read_json(self.paths.runtime / "task.timing.json")
        self.assertGreater(timing["total_seconds"], 0)
        self.assertEqual(timing["commands"][0]["exit_code"], 0)
        self.assertGreaterEqual(timing["commands"][0]["duration_seconds"], 0)
        for raw in (self.paths.runtime / "task.events.jsonl").read_text().splitlines():
            self.assertIn("voice_agent_elapsed_seconds", json.loads(raw))

    def test_desktop_launcher_keeps_arguments_and_checks_persistent_service(self):
        results = [subprocess.CompletedProcess([], 0, "", ""),
                   subprocess.CompletedProcess([], 0, "ActiveState=active\nMainPID=123\n", "")]
        with patch.object(agent.shutil, "which", return_value="/usr/bin/mpv"), \
                patch.object(agent.subprocess, "run", side_effect=results) as run, \
                patch("builtins.print"):
            self.assertEqual(agent.launch_program(["--", "mpv", "/tmp/a video.mp4"]), 0)
        command = run.call_args_list[0].args[0]
        self.assertIn("--service-type=exec", command)
        self.assertEqual(command[-3:], ["--", "/usr/bin/mpv", "/tmp/a video.mp4"])
        self.assertNotIn("shell", run.call_args_list[0].kwargs)

    def test_desktop_launcher_does_not_claim_success_for_an_exited_application(self):
        results = [subprocess.CompletedProcess([], 0, "", ""),
                   subprocess.CompletedProcess([], 0, "ActiveState=inactive\nMainPID=0\n", "")]
        with patch.object(agent.shutil, "which", return_value="/usr/bin/mpv"), \
                patch.object(agent.subprocess, "run", side_effect=results):
            with self.assertRaisesRegex(ValueError, "did not stay running"):
                agent.launch_program(["mpv", "missing.mp4"])


if __name__ == "__main__":
    unittest.main()
