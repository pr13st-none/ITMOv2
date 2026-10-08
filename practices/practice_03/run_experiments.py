"""Run the reproducible Practice 3 A/B experiment with local Ollama and OpenCode."""

import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEMO = HERE / "lab" / "demo"
OLLAMA_URL = "http://127.0.0.1:11434"


def api(path, payload=None):
    request = urllib.request.Request(
        OLLAMA_URL + path,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def executable_command(command):
    resolved = shutil.which(command[0]) or command[0]
    invocation = [resolved, *command[1:]]
    if Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(invocation)]
    return invocation


def cmd_output(command, cwd=HERE, timeout=300):
    try:
        result = subprocess.run(
            executable_command(command),
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return {
            "command": command,
            "exit_code": 127,
            "stdout": "",
            "stderr": str(error),
        }


def total_memory_bytes():
    if os.name != "nt":
        try:
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (AttributeError, ValueError):
            return None

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("available_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return status.total_physical


def experiment_env(root):
    env = os.environ.copy()
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "true"
    env["OPENCODE_DISABLE_SHARE"] = "true"
    env["OPENCODE_DISABLE_MODELS_FETCH"] = "true"
    env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
    env["XDG_DATA_HOME"] = str(root / "xdg-data")
    env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
    return env


def run_cli(command, cwd, env, output):
    started = time.perf_counter()
    invocation = executable_command(command)
    try:
        result = subprocess.run(
            invocation,
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=600,
            check=False,
        )
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        stderr, code = "TIMEOUT after 600 seconds", 124

    events = []
    non_json = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            non_json.append(line)

    record = {
        "command": command,
        "exit_code": code,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "events": events,
        "stderr": stderr.strip(),
        "non_json_stdout": non_json,
    }
    save(output, record)
    if code != 0:
        raise RuntimeError(f"OpenCode failed: {output.name}, exit {code}\n{stderr}")
    return record


def config(model, prompt):
    return {
        "$schema": "https://opencode.ai/config.json",
        "model": "ollama/" + model,
        "small_model": "ollama/" + model,
        "default_agent": "local-guide",
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama local",
                "options": {"baseURL": OLLAMA_URL + "/v1"},
                "models": {
                    model: {
                        "name": "ITMO read-only local agent",
                        "limit": {"context": 16384, "output": 1024},
                    }
                },
            }
        },
        "agent": {
            "local-guide": {
                "description": "Read-only local agent for the bundled demo repository",
                "mode": "primary",
                "prompt": prompt,
                "steps": 8,
                "permission": {
                    "read": "allow",
                    "glob": "allow",
                    "grep": "allow",
                    "list": "allow",
                    "edit": "deny",
                    "bash": "deny",
                    "task": "deny",
                    "webfetch": "deny",
                    "websearch": "deny",
                    "skill": "deny",
                    "todowrite": "deny",
                    "question": "deny",
                    "lsp": "deny",
                    "external_directory": "deny",
                },
            }
        },
    }


def final_text(record):
    chunks = []
    for event in record["events"]:
        part = event.get("part", {})
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            chunks.append(part["text"])
        elif event.get("type") == "text" and isinstance(event.get("text"), str):
            chunks.append(event["text"])
    return "\n".join(chunks).strip() or "\n".join(record["non_json_stdout"]).strip()


def read_seen(record):
    return any(
        event.get("part", {}).get("tool") == "read"
        or event.get("tool") == "read"
        for event in record["events"]
    )


def evaluate(question_id, answer):
    text = answer.lower()
    checks = {
        "Q1": (("make test",), ("readme", "makefile")),
        "Q2": (("valueerror",), ("service.py",)),
        "Q3": (("unsubscribe",), ("нет", "отсутств", "не реализ")),
        "Q4": (("ci",), ("нет", "отсутств", "не указан", "нельзя определить")),
        "Q5": (("set", "памят"), ("нет", "не сохраня")),
    }[question_id]
    return all(any(term in text for term in alternatives) for alternatives in checks)


def compact(value, limit=500):
    return value.replace("\n", " ").replace("|", "\\|")[:limit]


def clean_markdown(value):
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def trim_model_show(model_show):
    model_info = model_show.get("model_info", {})
    return {
        "details": model_show.get("details", {}),
        "parameters": model_show.get("parameters", ""),
        "capabilities": model_show.get("capabilities", []),
        "modified_at": model_show.get("modified_at"),
        "model_info": {
            key: model_info[key]
            for key in (
                "general.architecture",
                "general.parameter_count",
                "qwen3.context_length",
            )
            if key in model_info
        },
    }


def write_answers(out, questions, answers, summary):
    lines = [
        "# Ответы локальной модели",
        "",
        "Каждый вопрос задавался в отдельной read-only OpenCode-сессии. Эталоны из `questions.json` в тестовые сессии не передавались.",
        "",
    ]
    for question in questions:
        qid = question["id"]
        lines += [
            f"## {qid}. {question['question']}",
            "",
            f"**Эталон рабочего агента:** {question['expected']}",
            "",
            f"**A:** {clean_markdown(answers['A'][qid])}",
            "",
            f"**B:** {clean_markdown(answers['B'][qid])}",
            "",
            f"**Сверка:** A — {'OK' if summary['quality']['A'][qid] else 'ошибка/граница'}, B — {'OK' if summary['quality']['B'][qid] else 'ошибка/граница'}.",
            "",
        ]
    (HERE / "ANSWERS.md").write_text("\n".join(lines), encoding="utf-8")


def write_report(out, questions, answers, summary, environment):
    details = environment["model_show"].get("details", {})
    ram = environment.get("ram_bytes")
    ram_gib = f"{ram / 1024**3:.1f} GiB" if ram else "не определена"
    score_a = sum(summary["quality"]["A"].values())
    score_b = sum(summary["quality"]["B"].values())
    lines = [
        "# REPORT — практика 3",
        "",
        "## Локальный сетап",
        "",
        f"- ОС: `{environment['platform']}`;",
        f"- CPU: `{environment['cpu']}`, логических ядер: `{environment['logical_cpu_count']}`;",
        f"- RAM: `{ram_gib}`;",
        f"- GPU: `{environment['gpu']['stdout'] or environment['gpu']['stderr']}`;",
        f"- OpenCode: `{environment['opencode']['stdout']}`;",
        f"- Ollama: `{environment['ollama']['stdout']}`;",
        f"- Python: `{environment['python']}`; GNU Make: `{environment['make']['stdout'].splitlines()[0]}`;",
        f"- базовая модель: `{environment['base_model']}`; локальный ID: `{environment['model']}`;",
        f"- параметры: `{details.get('parameter_size', 'unknown')}`, квантизация `{details.get('quantization_level', 'unknown')}`, context `16384`, temperature `0.2`, seed `42`, num_predict `1024`.",
        "",
        "Модель 4B/Q4_K_M выбрана как компромисс: она полностью помещается в 16 GB VRAM, поддерживает tool calls и работает без облачного API. Контекст 16384 нужен, потому что 4096 токенов не вмещают системный prompt OpenCode, схемы read-only tools и файлы задачи.",
        "",
        "## Проверка проекта",
        "",
        "```text",
        "\n".join(
            part for part in (
                environment["make_test"]["stdout"],
                environment["make_test"]["stderr"],
            ) if part
        ),
        "```",
        "",
        "## Контроль A/B",
        "",
        "В обоих вариантах одинаковы модель, квантизация, demo-файлы, вопросы, context, temperature, seed, num_predict, OpenCode и read-only permissions. Изменён ровно один фактор — system prompt.",
        "",
        "- A: прочитать файлы, кратко ответить и указать источник.",
        "- B: дополнительно проверять предпосылки, требовать file:line и не выдумывать отсутствующие данные.",
        "",
        "## Пять вопросов",
        "",
        "| Вопрос | A | B |",
        "|---|---|---|",
    ]
    for question in questions:
        qid = question["id"]
        a_mark = "OK" if summary["quality"]["A"][qid] else "ошибка/граница"
        b_mark = "OK" if summary["quality"]["B"][qid] else "ошибка/граница"
        lines.append(
            f"| {qid}: {compact(question['question'], 180)} | **{a_mark}** — {compact(answers['A'][qid])} | **{b_mark}** — {compact(answers['B'][qid])} |"
        )

    med_a = summary["timing"]["A"]["median_wall_seconds"]
    med_b = summary["timing"]["B"]["median_wall_seconds"]
    lines += [
        "",
        "## Результаты и ограничения",
        "",
        f"- фактическая сверка с эталоном: A — `{score_a}/5`, B — `{score_b}/5`;",
        f"- read-tool подтверждён: A — `{summary['read_tools']['A']}/5`, B — `{summary['read_tools']['B']}/5`;",
        f"- три прогретых запуска A: `{summary['timing']['A']['warmed_wall_seconds']}`, медиана `{med_a:.3f} s`;",
        f"- три прогретых запуска B: `{summary['timing']['B']['warmed_wall_seconds']}`, медиана `{med_b:.3f} s`;",
        "- измерялся полный wall time OpenCode-сессии, а не TTFT;",
        "- SHA-256 demo-файлов до и после совпал: тестируемый агент ничего не изменил.",
        "",
        "Ключевые проверки — Q3 с ложной предпосылкой и Q4 без ответа в репозитории. Именно они показывают, умеет ли модель отказаться от выдуманного факта. Даже результат 5/5 на маленьком demo не доказывает надёжность на большом проекте: не проверялись длинные зависимости, большой объём кода и сложные refactoring-сценарии.",
        "",
        f"Для демонстрации оставлена конфигурация **{'B' if score_b >= score_a else 'A'}**: она не хуже по фактической сверке и явно требует проверять предпосылки и источники.",
        "",
        f"Сырые события, tool calls, ответы, конфиги и замеры лежат в `{out.relative_to(HERE).as_posix()}/`.",
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:4b-instruct")
    parser.add_argument("--agent-model", default="itmo-review-agent")
    parser.add_argument("--opencode", default="opencode")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    out = args.output or HERE / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=False)

    make_command = shutil.which("make")
    if not make_command and os.name == "nt":
        candidate = Path(r"C:\Program Files (x86)\GnuWin32\bin\make.exe")
        make_command = str(candidate) if candidate.exists() else None
    if not make_command:
        raise RuntimeError("GNU Make not found")

    environment = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "cpu": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
        "logical_cpu_count": os.cpu_count(),
        "ram_bytes": total_memory_bytes(),
        "base_model": args.model,
        "model": args.agent_model,
        "python": platform.python_version(),
        "opencode": cmd_output([args.opencode, "--version"]),
        "ollama": cmd_output(["ollama", "--version"]),
        "make": cmd_output([make_command, "--version"]),
        "make_test": cmd_output([make_command, "test"]),
        "gpu": cmd_output([
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader",
        ]),
        "ollama_tags": {
            "models": [
                model for model in api("/api/tags").get("models", [])
                if model.get("name", "").split(":", 1)[0] == args.agent_model
            ]
        },
        "model_show": trim_model_show(api("/api/show", {"model": args.agent_model})),
    }
    save(out / "environment.json", environment)
    if environment["make_test"]["exit_code"] != 0:
        raise RuntimeError("make test failed")

    demo_files = sorted(
        path for path in DEMO.rglob("*")
        if path.is_file() and path.name != "opencode.json" and "__pycache__" not in path.parts
    )
    manifest = {
        str(path.relative_to(DEMO)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in demo_files
    }
    save(out / "input-manifest.json", manifest)

    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    prompts = {
        variant: (HERE / "prompts" / f"{variant}.txt").read_text(encoding="utf-8").strip()
        for variant in ("A", "B")
    }
    configs = {variant: config(args.agent_model, prompts[variant]) for variant in ("A", "B")}
    save(out / "config-A.json", configs["A"])
    save(out / "config-B.json", configs["B"])

    compare_a = json.loads(json.dumps(configs["A"]))
    compare_b = json.loads(json.dumps(configs["B"]))
    compare_a["agent"]["local-guide"]["prompt"] = "<PROMPT>"
    compare_b["agent"]["local-guide"]["prompt"] = "<PROMPT>"
    if compare_a != compare_b:
        raise RuntimeError("A/B configs differ by more than the prompt")

    answers = {"A": {}, "B": {}}
    timing = {"A": [], "B": []}
    read_counts = {"A": 0, "B": 0}

    with tempfile.TemporaryDirectory(prefix="practice3-") as temporary:
        temp = Path(temporary)
        repo = temp / "demo"
        shutil.copytree(DEMO, repo, ignore=shutil.ignore_patterns("__pycache__"))
        env = experiment_env(temp)

        (repo / "opencode.json").write_text(
            json.dumps(configs["B"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        reference_prompt = "Прочитай README.md, Makefile, service.py и test_service.py. Ответь на все вопросы, не изменяя файлы:\n" + "\n".join(
            f"{question['id']}. {question['question']}" for question in questions
        )
        run_cli(
            [args.opencode, "run", "--agent", "local-guide", "--format", "json", "--auto", reference_prompt],
            repo,
            env,
            out / "reference-opencode.json",
        )

        for variant in ("A", "B"):
            (repo / "opencode.json").write_text(
                json.dumps(configs[variant], ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for question in questions:
                qid = question["id"]
                record = run_cli(
                    [args.opencode, "run", "--agent", "local-guide", "--format", "json", "--auto", question["question"]],
                    repo,
                    env,
                    out / f"{variant}-{qid}.json",
                )
                answers[variant][qid] = final_text(record)
                read_counts[variant] += int(read_seen(record))

            for repeat in range(1, 4):
                record = run_cli(
                    [args.opencode, "run", "--agent", "local-guide", "--format", "json", "--auto", questions[0]["question"]],
                    repo,
                    env,
                    out / f"{variant}-speed-{repeat}.json",
                )
                timing[variant].append(record["wall_seconds"])

        after = {
            relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest()
            for relative in manifest
        }
        integrity = {"unchanged": manifest == after, "before": manifest, "after": after}
        save(out / "input-integrity.json", integrity)
        if not integrity["unchanged"]:
            raise RuntimeError("demo files changed during the read-only experiment")

    summary = {
        "timing": {
            variant: {
                "warmed_wall_seconds": timing[variant],
                "median_wall_seconds": statistics.median(timing[variant]),
            }
            for variant in ("A", "B")
        },
        "read_tools": read_counts,
        "quality": {
            variant: {
                question["id"]: evaluate(question["id"], answers[variant][question["id"]])
                for question in questions
            }
            for variant in ("A", "B")
        },
    }
    save(out / "answers.json", answers)
    save(out / "summary.json", summary)
    save(out / "ollama-ps.json", api("/api/ps"))
    write_answers(out, questions, answers, summary)
    write_report(out, questions, answers, summary, environment)
    print(f"Practice 3 complete: {out}")


if __name__ == "__main__":
    main()
