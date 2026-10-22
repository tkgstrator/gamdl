"""Verify container runtime and synthetic HLS without external services or accounts."""

import argparse
import ctypes
import hashlib
import http.server
import importlib.metadata
import json
import os
import platform
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import uuid
from pathlib import Path

EVIDENCE = Path("/evidence")
report = {
    "commands": [],
    "httpRequests": [],
    "negativeCanaries": {},
    "status": "RUNNING",
}


def persist():
    (EVIDENCE / "result.json").write_text(json.dumps(report, indent=2) + "\n")


def run(args, timeout=30):
    completed = subprocess.run(
        args, text=True, capture_output=True, timeout=timeout, check=False
    )
    report["commands"].append(
        {
            "args": args,
            "exit": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    )
    if completed.returncode:
        raise RuntimeError("command failed: " + args[0])
    return completed.stdout


class ValidationFailure(Exception):
    pass


def validate(output, requests, segments, expected_hash):
    served = {
        urllib.parse.urlparse(r["path"]).path
        for r in requests
        if r["method"] == "GET" and r["status"] == 200
    }
    if not {"/index.m3u8", *("/" + s for s in segments)} <= served:
        raise ValidationFailure("missing_http_segment")
    actual = hashlib.sha256(output.read_bytes()).hexdigest()
    if actual != expected_hash:
        raise ValidationFailure("concat_sha_mismatch")
    probe = json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(output),
            ]
        )
    )
    streams = probe["streams"]
    if not (
        len(streams) == 1
        and streams[0]["codec_type"] == "audio"
        and streams[0]["codec_name"] == "aac"
        and streams[0]["sample_rate"] == "48000"
        and streams[0]["channels"] == 1
    ):
        raise ValidationFailure("audio_shape_mismatch")
    duration = float(probe["format"]["duration"])
    if not 2.5 <= duration <= 3.5:
        raise ValidationFailure("duration_mismatch")
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-i",
            str(output),
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ]
    )
    return {
        "sha256": actual,
        "bytes": output.stat().st_size,
        "duration": duration,
        "ffprobe": probe,
    }


def fixture(args):
    server = thread = helper = None
    scratch = Path(tempfile.mkdtemp(prefix="gamdl-hls-", dir="/tmp"))
    try:
        report["runtime"] = {
            "version": importlib.metadata.version("gamdl"),
            "machine": platform.machine(),
            "helperSha256": hashlib.sha256(
                Path("/usr/local/bin/N_m3u8DL-RE").read_bytes()
            ).hexdigest(),
        }
        machine, elf_machine = ARCHES[args.expected_arch]
        binary = Path("/usr/local/bin/N_m3u8DL-RE").read_bytes()
        require(
            binary[:6] == b"\x7fELF\x02\x01" and len(binary) > 20, "Invalid helper ELF"
        )
        require(
            struct.unpack_from("<H", binary, 18)[0] == elf_machine,
            "Helper ELF architecture mismatch",
        )
        require(
            report["runtime"]["machine"] == machine,
            "Container process architecture mismatch",
        )
        require(
            report["runtime"]["version"] == args.expected_version,
            "Installed package version mismatch",
        )
        require(
            platform.python_version().startswith(args.python_version + "."),
            "Python version mismatch",
        )
        os_release = Path("/etc/os-release").read_text()
        require(
            "VERSION_CODENAME=" + args.base_image.removesuffix("-slim") + "\n"
            in os_release,
            "Base distro mismatch",
        )
        libc = ctypes.CDLL("libc.so.6")
        libc.gnu_get_libc_version.restype = ctypes.c_char_p
        report["runtime"].update(
            elfMachine=elf_machine,
            helperBytes=len(binary),
            python=platform.python_version(),
            osRelease=os_release,
            glibc=libc.gnu_get_libc_version().decode("ascii"),
        )
        run([sys.executable, "-m", "gamdl", "--help"])
        report["ffmpegVersion"] = run(["ffmpeg", "-version"]).splitlines()[0]
        report["ffprobeVersion"] = run(["ffprobe", "-version"]).splitlines()[0]
        help_text = run(["N_m3u8DL-RE", "--help"])
        flags = [
            "no-config",
            "disable-update-check",
            "use-system-proxy",
            "ffmpeg-binary-path",
            "write-meta-json",
            "no-ansi-color",
            "ui-language",
            "save-dir",
            "save-name",
            "auto-select",
            "binary-merge",
            "no-log",
        ]
        require(
            (
                all(
                    re.search(r"(?<![\w-])--" + re.escape(f) + r"(?:\s|$)", help_text)
                    for f in flags
                )
            ),
            'Verification condition failed: all(             re.search(r"(?<![\\w-])--" + re.escape(f) + r"(?:\\s|$)", help_text)             for f in flags         )',
        )
        fixture, output_dir = scratch / "fixture", scratch / "download"
        fixture.mkdir()
        output_dir.mkdir()
        private_home = scratch / "private-home"
        private_home.mkdir()
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=3",
                "-ac",
                "1",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-f",
                "hls",
                "-hls_time",
                "1",
                "-hls_playlist_type",
                "vod",
                "-hls_list_size",
                "0",
                "-hls_segment_filename",
                str(fixture / "part%03d.ts"),
                str(fixture / "index.m3u8"),
            ]
        )
        playlist = (fixture / "index.m3u8").read_text()
        require(
            ("#EXT-X-ENDLIST" in playlist),
            'Verification condition failed: "#EXT-X-ENDLIST" in playlist',
        )
        segments = [
            line.strip()
            for line in playlist.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        require(
            (segments and len(set(segments)) == len(segments)),
            "Verification condition failed: segments and len(set(segments)) == len(segments)",
        )
        require(
            (
                all(
                    Path(s).name == s and re.fullmatch(r"part[0-9]+\.ts", s)
                    for s in segments
                )
            ),
            'Verification condition failed: all(             Path(s).name == s and re.fullmatch(r"part[0-9]+\\.ts", s) for s in segments         )',
        )
        expected_bytes = b"".join((fixture / s).read_bytes() for s in segments)
        expected_hash = hashlib.sha256(expected_bytes).hexdigest()
        report["fixture"] = {
            "playlist": playlist,
            "segments": segments,
            "orderedConcatSha256": expected_hash,
            "orderedConcatBytes": len(expected_bytes),
        }

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(fixture), **kwargs)

            def log_request(self, code="-", size="-"):
                report["httpRequests"].append(
                    {"method": self.command, "path": self.path, "status": int(code)}
                )

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        thread.start()
        url = "http://127.0.0.1:" + str(server.server_port) + "/index.m3u8"
        args = [
            "N_m3u8DL-RE",
            url,
            "--no-config",
            "--disable-update-check",
            "--use-system-proxy",
            "false",
            "--ffmpeg-binary-path",
            "/usr/bin/ffmpeg",
            "--write-meta-json",
            "false",
            "--no-ansi-color",
            "--ui-language",
            "en-US",
            "--save-dir",
            str(output_dir),
            "--save-name",
            "verified",
            "--auto-select",
            "--binary-merge",
            "--no-log",
        ]
        child_env = os.environ.copy()
        child_env["TERM"] = "dumb"
        child_env["HOME"] = str(private_home)
        child_env["XDG_CONFIG_HOME"] = str(private_home / ".config")
        helper = subprocess.Popen(
            args,
            cwd=scratch,
            env=child_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = helper.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(helper.pid, signal.SIGTERM)
            try:
                helper.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(helper.pid, signal.SIGKILL)
                helper.communicate()
            raise RuntimeError("helper timeout")
        report["helper"] = {
            "args": args,
            "exit": helper.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
        (EVIDENCE / "helper.stdout.log").write_text(stdout)
        (EVIDENCE / "helper.stderr.log").write_text(stderr)
        require(
            (helper.returncode == 0),
            "Verification condition failed: helper.returncode == 0",
        )
        files = [p for p in output_dir.rglob("*") if p.is_file() and p.stat().st_size]
        report["outputFiles"] = [str(p.relative_to(output_dir)) for p in files]
        require((len(files) == 1), "Verification condition failed: len(files) == 1")
        output = files[0]
        report["validatedOutput"] = validate(
            output, report["httpRequests"], segments, expected_hash
        )

        truncated = scratch / "truncated.ts"
        truncated.write_bytes(output.read_bytes()[: output.stat().st_size // 2])
        try:
            validate(truncated, report["httpRequests"], segments, expected_hash)
            raise AssertionError("truncated output was accepted")
        except ValidationFailure as e:
            require(
                (str(e) == "concat_sha_mismatch"),
                'Verification condition failed: str(e) == "concat_sha_mismatch"',
            )
            report["negativeCanaries"]["truncatedOutputRejected"] = str(e)
        missing_log = [
            r
            for r in report["httpRequests"]
            if urllib.parse.urlparse(r["path"]).path != "/" + segments[0]
        ]
        try:
            validate(output, missing_log, segments, expected_hash)
            raise AssertionError("missing segment GET was accepted")
        except ValidationFailure as e:
            require(
                (str(e) == "missing_http_segment"),
                'Verification condition failed: str(e) == "missing_http_segment"',
            )
            report["negativeCanaries"]["missingHTTPGetRejected"] = str(e)
        shutil.copytree(fixture, EVIDENCE / "fixture")
        shutil.copy2(output, EVIDENCE / ("verified-output" + output.suffix))
        report["retainedEvidence"] = [
            {
                "path": str(p.relative_to(EVIDENCE)),
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in EVIDENCE.rglob("*")
            if p.is_file()
        ]
        report["status"] = "PASS_OFFLINE_HLS"
    finally:
        if helper is not None and helper.poll() is None:
            os.killpg(helper.pid, signal.SIGTERM)
            try:
                helper.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(helper.pid, signal.SIGKILL)
                helper.wait()
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=5)
            require(
                (not thread.is_alive()),
                "Verification condition failed: not thread.is_alive()",
            )
        shutil.rmtree(scratch)
        report["cleanup"] = {
            "helperStopped": helper is None or helper.poll() is not None,
            "httpThreadStopped": thread is None or not thread.is_alive(),
            "scratchRemoved": not scratch.exists(),
        }
        persist()
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "error": report.get("error"),
                    "validatedOutput": {
                        k: v
                        for k, v in report.get("validatedOutput", {}).items()
                        if k != "ffprobe"
                    },
                    "negativeCanaries": report["negativeCanaries"],
                }
            ),
            flush=True,
        )
    require(
        report["status"] == "PASS_OFFLINE_HLS", report.get("error", "Fixture failed")
    )


ARCHES = {"amd64": ("x86_64", 62), "arm64": ("aarch64", 183)}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def source_inputs():
    paths = run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
    return {
        "head": run(["git", "rev-parse", "HEAD"]).strip(),
        "tree": run(["git", "rev-parse", "HEAD^{tree}"]).strip(),
        "files": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in sorted(set(paths.split("\0")) - {""})
        },
    }


def host_preflight(args, minimum_gib):
    actual_host = platform.machine().lower()
    native_names = (
        {"arm64", "aarch64"} if args.expected_arch == "arm64" else {"x86_64", "amd64"}
    )
    require(
        actual_host in native_names,
        "Host architecture mismatch; emulation cannot satisfy this native gate",
    )
    if args.require_linux_host:
        require(platform.system() == "Linux", "CI requires a native Linux host")
    docker = json.loads(run(["docker", "info", "--format", "{{json .}}"], timeout=60))
    require(docker["OSType"] == "linux", "Docker server must use Linux")
    require(
        docker["Architecture"] in native_names, "Docker server architecture mismatch"
    )
    free = shutil.disk_usage(EVIDENCE).free
    require(
        free >= minimum_gib * 1024**3,
        f"Less than {minimum_gib} GiB free for verification",
    )
    report["host"] = {
        "system": platform.system(),
        "machine": actual_host,
        "dockerContext": run(["docker", "context", "show"]).strip(),
        "dockerMachine": docker["Architecture"],
        "dockerVersion": docker["ServerVersion"],
        "freeBytes": free,
    }


def prepare(args):
    host_preflight(args, 10)
    (EVIDENCE / "source-inputs.json").write_text(
        json.dumps(source_inputs(), indent=2) + "\n"
    )
    report["github"] = {
        key: os.environ.get(key)
        for key in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "PR_HEAD_SHA")
    }
    report["expected"] = {
        "arch": args.expected_arch,
        "version": args.expected_version,
        "python": args.python_version,
        "baseImage": args.base_image,
    }
    report["status"] = "PASS_PREFLIGHT_ONLY"


def verify_image(args):
    host_preflight(args, 1)
    inputs = json.loads((EVIDENCE / "source-inputs.json").read_text())
    require(inputs == source_inputs(), "Source changed after build preflight")
    image = json.loads(run(["docker", "image", "inspect", args.image]))[0]
    require(
        image["Os"] == "linux" and image["Architecture"] == args.expected_arch,
        "Image platform mismatch",
    )
    report["image"] = {
        key: image.get(key)
        for key in ("Id", "RepoDigests", "Os", "Architecture", "RootFS")
    }
    runtime_evidence = EVIDENCE / "runtime"
    runtime_evidence.mkdir()
    container_name = "gamdl-hls-" + uuid.uuid4().hex
    report["ownedContainer"] = container_name
    try:
        run(
            [
                "docker",
                "create",
                "--name",
                container_name,
                "--label",
                "gamdl.hls.run=" + container_name,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "128",
                "--memory",
                "1g",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=128m,mode=1777",
                "--mount",
                f"type=bind,source={Path(__file__).resolve()},target=/verify-container-hls.py,readonly",
                "--mount",
                f"type=bind,source={runtime_evidence},target=/evidence",
                "--env",
                "HOME=/tmp",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "--entrypoint",
                "python",
                image["Id"],
                "/verify-container-hls.py",
                "--fixture",
                "--evidence-dir",
                "/evidence",
                "--expected-version",
                args.expected_version,
                "--expected-arch",
                args.expected_arch,
                "--python-version",
                args.python_version,
                "--base-image",
                args.base_image,
            ]
        )
        container = json.loads(run(["docker", "inspect", container_name]))[0]
        require(container["Image"] == image["Id"], "Container image identity mismatch")
        report["containerImage"] = container["Image"]
        run(["docker", "start", "--attach", container_name], timeout=180)
        container = json.loads(run(["docker", "inspect", container_name]))[0]
        require(container["State"]["ExitCode"] == 0, "Fixture container failed")
        runtime = json.loads((runtime_evidence / "result.json").read_text())
        require(runtime["status"] == "PASS_OFFLINE_HLS", "Fixture report did not pass")
        require(inputs == source_inputs(), "Source changed during runtime verification")
        report["runtimeResult"] = "runtime/result.json"
        report["status"] = "PASS_NATIVE_IMAGE_HLS"
    finally:
        inspected = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if inspected.returncode == 0:
            owned = json.loads(inspected.stdout)[0]
            require(
                owned["Config"]["Labels"].get("gamdl.hls.run") == container_name,
                "Container ownership mismatch",
            )
            run(["docker", "rm", "--force", container_name], timeout=60)
        remaining = run(
            [
                "docker",
                "ps",
                "--all",
                "--filter",
                "name=^/" + container_name + "$",
                "--format",
                "{{.Names}}",
            ]
        )
        require(not remaining.strip(), "Owned container remains")
        report["cleanup"] = {"ownedContainerRemoved": True}


def interrupted(signum, frame):
    raise RuntimeError(f"Interrupted by signal {signum}")


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--image")
    mode.add_argument("--fixture", action="store_true")
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-arch", choices=ARCHES, required=True)
    parser.add_argument("--python-version", choices=("3.10", "3.14"), required=True)
    parser.add_argument(
        "--base-image", choices=("bookworm-slim", "trixie-slim"), required=True
    )
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--require-linux-host", action="store_true")
    args = parser.parse_args()
    EVIDENCE = args.evidence_dir.resolve()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, interrupted)
    report["status"] = "FAIL"
    try:
        if args.prepare:
            prepare(args)
        elif args.fixture:
            fixture(args)
        else:
            verify_image(args)
    except (
        RuntimeError,
        OSError,
        ValueError,
        LookupError,
        AssertionError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
        ImportError,
    ) as error:
        report["status"] = "FAIL"
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        filename = "preflight.json" if args.prepare else "result.json"
        (EVIDENCE / filename).write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({"status": report["status"], "error": report.get("error")}),
        flush=True,
    )
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
