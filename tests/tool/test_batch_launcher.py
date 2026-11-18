"""Exercise legacy PowerShell argv and quota-stop behavior without a model."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PWSH = shutil.which("pwsh")


@unittest.skipUnless(os.name == "nt" and PWSH, "Windows PowerShell native-argument regression")
class BatchLauncherTests(unittest.TestCase):
    def run_batch(self, reformat=False, quota_error=False):
        temporary_root = ROOT / "temp" / "batch-launcher-tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="batch with spaces ", dir=temporary_root)
        self.addCleanup(temporary.cleanup)
        working = Path(temporary.name)
        sources = working / "input with spaces"
        sources.mkdir()
        source = sources / "episode one.eng.srt"
        source.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello!\n", encoding="utf-8")
        if quota_error:
            (sources / "episode two.eng.srt").write_bytes(source.read_bytes())
        output = working / "output with spaces"
        capture = working / "argv.jsonl"
        # Isolated native child: the actual launcher runs, model entry points do not.
        stub = ("import json, pathlib, sys\n"
                "with pathlib.Path('argv.jsonl').open('a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                + ("print('RESOURCE_EXHAUSTED: quota exceeded')\nsys.exit(1)\n"
                   if quota_error else "print('stub completed')\n"))
        for filename in ("main.py", "reformat_srt.py"):
            (working / filename).write_text(stub, encoding="utf-8")
        environment = dict(os.environ)
        environment.pop("VIRTUAL_ENV", None)
        environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
        command = [PWSH, "-NoProfile", "-File", str(ROOT / "translate_all_srt.ps1"),
                   "-SubtitlesPath", str(sources), "-OutputPath", str(output)]
        if reformat:
            command.append("-ReformatOnly")
        result = subprocess.run(command, cwd=working, env=environment, input="Y\n",
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        arguments = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines()] if capture.exists() else []
        return result, arguments, source, output

    def test_translation_receives_literal_input_and_output_paths_with_spaces(self):
        result, calls, source, output = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], str(source))
        self.assertEqual(calls[0][calls[0].index("--output-dir") + 1], str(output))

    def test_reformatter_receives_literal_path_with_spaces(self):
        result, calls, source, _ = self.run_batch(reformat=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, [[str(source)]])

    def test_quota_failure_stops_before_the_second_file(self):
        result, calls, _, _ = self.run_batch(quota_error=True)
        self.assertEqual(result.returncode, 103, result.stdout + result.stderr)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
