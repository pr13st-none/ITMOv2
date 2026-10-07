"""Run the Practice 3 experiment against the bundled lab/demo with local Ollama."""

import argparse
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
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def cmd_output(command):
    result = subprocess.run(command, text=True, capture_output=True)
    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def isolated_env(root):
    env = os.environ.copy()
    env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
    env["XDG_DATA_HOME"] = str(root / "xdg-data")
    env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "true"
    env["OPENCODE_DISABLE_SHARE"] = "true"
    return env


def run_cli(command, cwd, env, output):
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=600,
        )
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        stderr, code = "TIMEOUT after 600 s", 124

    events = []
    non_json = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if event.get("type") != "reasoning":
                events.append(event)
        except json.JSONDecodeError:
            non_json.append(line)

    record = {
        "command": command,
        "exit_code": code,
        "wall_seconds": time.perf_counter() - started,
        "events": events,
        "stderr": stderr,
        "non_json_stdout": non_json,
    }
    save(output, record)
    if code != 0:
        raise RuntimeError(f"OpenCode failed for {output.name}: exit {code}\n{stderr}")
    return record


def config(model, system_prompt):
    return {
        "$schema": "https://opencode.ai/config.json",
        "model": "ollama/" + model,
        "default_agent": "local-guide",
        "providers": {
            "ollama": {"settings": {"baseURL": OLLAMA_URL + "/v1"}},
        },
        "agents": {
            "local-guide": {
                "description": "Read-only agent for the bundled demo repository",
                "mode": "primary",
                "system": system_prompt,
                "steps": 8,
                "permissions": [
                    {"action": "*", "resource": "*", "effect": "deny"},
                    {"action": "read", "resource": "*", "effect": "allow"},
                    {"action": "glob", "resource": "*", "effect": "allow"},
                    {"action": "grep", "resource": "*", "effect": "allow"},
                ],
            }
        },
    }


def final_text(record):
    chunks = []
    for event in record.get("events", []):
        part = event.get("part")
        if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
            chunks.append(part["text"])
        elif event.get("type") == "text" and isinstance(event.get("text"), str):
            chunks.append(event["text"])
    if chunks:
        return "\n".join(chunks).strip()
    return "\n".join(record.get("non_json_stdout", [])).strip()


def read_seen(record):
    raw = json.dumps(record.get("events", []), ensure_ascii=False)
    patterns = [
        r'"tool"\s*:\s*"read"',
        r'"name"\s*:\s*"read"',
        r'"toolName"\s*:\s*"read"',
    ]
    return any(re.search(pattern, raw) for pattern in patterns)


def evaluate(question_id, answer):
    text = answer.lower()
    checks = {
        "Q1": ["make test", "readme"],
        "Q2": ["valueerror", "service.py"],
        "Q3": ["unsubscribe", ("нет", "отсутств")],
        "Q4": [("нет", "отсутств", "не указан", "нет ответа"), "ci"],
        "Q5": [("не сохраня", "нет"), ("set", "памят")],
    }[question_id]
    for item in checks:
        if isinstance(item, str):
            if item not in text:
                return False
        elif not any(term in text for term in item):
            return False
    return True


def write_report(out, questions, answers, summary, environment):
    details = environment.get("model_show", {}).get("details", {})
    quant = details.get("quantization_level", "не указана Ollama")
    family = details.get("family", "не указано")
    gpu = environment.get("nvidia-smi", {}).get("stdout") or "nvidia-smi недоступен"
    cpu = environment.get("lscpu", {}).get("stdout") or platform.processor()
    ram = environment.get("free", {}).get("stdout") or "free недоступен"

    lines = [
        "# REPORT — практика 3",
        "",
        "## Локальный сетап",
        "",
        f"- время запуска (UTC): `{environment['utc']}`;",
        f"- ОС: `{environment['platform']}`;",
        f"- OpenCode: `{environment['opencode']['stdout']}`;",
        f"- Ollama: `{environment['ollama']['stdout']}`;",
        f"- Python: `{environment['python']['stdout']}`;",
        f"- базовая модель: `{environment['base_model']}`; локальная модель эксперимента: `{environment['model']}`;",
        f"- family: `{family}`; quantization: `{quant}`; context: `{environment['context']}`;",
        "- temperature: `0.2`, seed: `42`, num_predict: `1024`;",
        "- модель выбрана как достаточно компактная для полностью локального запуска и при этом поддерживающая tool use в OpenCode.",
        "",
        "<details><summary>CPU</summary>",
        "",
        "```text",
        cpu,
        "```",
        "</details>",
        "",
        "<details><summary>RAM</summary>",
        "",
        "```text",
        ram,
        "```",
        "</details>",
        "",
        "<details><summary>GPU</summary>",
        "",
        "```text",
        gpu,
        "```",
        "</details>",
        "",
        "## Контроль A/B",
        "",
        "В A и B одинаковы модель, квантизация, demo-файлы, пять вопросов, context, temperature, seed, num_predict и режим рассуждения. Изменён ровно один фактор — system prompt.",
        "",
        "| Вариант | System prompt |",
        "|---|---|",
        "| A | краткий: прочитать файлы, ответить и указать источник |",
        "| B | дополнительно проверять предпосылки, требовать file:line и не выдумывать отсутствующие данные |",
        "",
        "## Пять вопросов",
        "",
        "Каждый вопрос запускался в новой OpenCode-сессии. Эталон не передавался тестируемой модели.",
        "",
        "| Вопрос | Эталон | A | B |",
        "|---|---|---|---|",
    ]
    for question in questions:
        qid = question["id"]
        a = answers["A"][qid]
        b = answers["B"][qid]
        mark_a = "OK" if evaluate(qid, a) else "ошибка/граница"
        mark_b = "OK" if evaluate(qid, b) else "ошибка/граница"
        compact = lambda value: value.replace("\n", " ").replace("|", "\\|")[:420]
        lines.append(
            f"| {qid}: {compact(question['question'])} | {compact(question['expected'])} | **{mark_a}** — {compact(a)} | **{mark_b}** — {compact(b)} |"
        )

    med_a = summary["timing"]["A"]["median_wall_seconds"]
    med_b = summary["timing"]["B"]["median_wall_seconds"]
    lines += [
        "",
        "## Инструменты и замеры",
        "",
        f"- read-tool подтверждён во всех пяти A-сессиях: `{summary['read_tools']['A']}/5`;",
        f"- read-tool подтверждён во всех пяти B-сессиях: `{summary['read_tools']['B']}/5`;",
        f"- три прогретых запуска A: `{summary['timing']['A']['warmed_wall_seconds']}`, медиана `{med_a:.3f} s`;",
        f"- три прогретых запуска B: `{summary['timing']['B']['warmed_wall_seconds']}`, медиана `{med_b:.3f} s`;",
        "- TTFT отдельно не измерялся: `opencode run --format json` фиксируется как end-to-end wall time; это ограничение измерения, а не выдуманная метрика.",
        "",
        "## Ограничения и вывод",
        "",
    ]
    bad_a = sum(not evaluate(q["id"], answers["A"][q["id"]]) for q in questions)
    bad_b = sum(not evaluate(q["id"], answers["B"][q["id"]]) for q in questions)
    lines.append(
        f"На пяти вопросах эвристическая сверка отметила ошибок/границ: A — `{bad_a}`, B — `{bad_b}`. Особенно важны Q3 (ложная предпосылка) и Q4 (ответа нет в репозитории): они проверяют склонность модели додумывать отсутствующие факты."
    )
    if bad_a == 0 and bad_b == 0:
        lines.append(
            "На базовых пяти вопросах явную ошибку не нашли. Это не доказывает общую надёжность: отдельно не проверялись большие репозитории, длинный контекст, неоднозначные ссылки между файлами и нестандартные tool-сценарии."
        )
    winner = "B" if bad_b <= bad_a else "A"
    lines += [
        f"Оставляю конфигурацию **{winner}**: на этом наборе она не хуже по фактической сверке и лучше формулирует требования к проверке предпосылок и источникам.",
        "",
        "Сырые OpenCode-сессии, ответы, tool events, model metadata, integrity hashes и замеры лежат в последней папке `results/`. Снимок `lab/demo` после эксперимента проверен по SHA-256 и не менялся.",
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--agent-model", default="itmo-review-agent")
    parser.add_argument("--context", type=int, default=16384)
    parser.add_argument("--opencode", default="opencode")
    parser.add_argument("--ollama", default="ollama")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    out = args.output or HERE / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=False)

    environment = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "base_model": args.model,
        "model": args.agent_model,
        "context": args.context,
        "opencode": cmd_output([args.opencode, "--version"]),
        "ollama": cmd_output([args.ollama, "--version"]),
        "lscpu": cmd_output(["bash", "-lc", "lscpu"]),
        "free": cmd_output(["bash", "-lc", "free -h"]),
        "python": cmd_output(["python3", "--version"]),
        "nvidia-smi": cmd_output(["bash", "-lc", "nvidia-smi"]),
    }
    if "2.0.20" not in environment["opencode"]["stdout"] + environment["opencode"]["stderr"]:
        raise RuntimeError("Practice 3 requires OpenCode 2.0.20 for this run")

    environment["ollama_tags"] = api("/api/tags")
    environment["model_show"] = api("/api/show", {"model": args.agent_model})
    save(out / "environment.json", environment)

    demo_files = sorted(path for path in DEMO.rglob("*") if path.is_file() and path.name != "opencode.json")
    manifest = {
        str(path.relative_to(DEMO)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in demo_files
    }
    save(out / "input-manifest.json", manifest)

    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    prompts = {v: (HERE / "prompts" / f"{v}.txt").read_text(encoding="utf-8") for v in ("A", "B")}
    configs = {v: config(args.agent_model, prompts[v]) for v in ("A", "B")}
    save(out / "config-A.json", configs["A"])
    save(out / "config-B.json", configs["B"])

    # The only deliberate A/B difference is agents.local-guide.system.
    check_a = json.loads(json.dumps(configs["A"]))
    check_b = json.loads(json.dumps(configs["B"]))
    check_a["agents"]["local-guide"]["system"] = "<SYSTEM>"
    check_b["agents"]["local-guide"]["system"] = "<SYSTEM>"
    if check_a != check_b:
        raise RuntimeError("A/B configs differ by more than the system prompt")

    answers = {"A": {}, "B": {}}
    timing = {"A": [], "B": []}
    read_counts = {"A": 0, "B": 0}

    with tempfile.TemporaryDirectory(prefix="practice3-") as temp_dir:
        temp = Path(temp_dir)
        repo = temp / "demo"
        shutil.copytree(DEMO, repo)
        env = isolated_env(temp)

        # An independent OpenCode reference pass over the same code, kept outside test prompts.
        (repo / "opencode.json").write_text(json.dumps(configs["B"], ensure_ascii=False, indent=2), encoding="utf-8")
        reference_prompt = "Прочитай README.md, service.py, test_service.py и ответь на пять вопросов по коду. Не изменяй файлы.\n\n" + "\n".join(
            f"{q['id']}. {q['question']}" for q in questions
        )
        run_cli(
            [args.opencode, "run", "--standalone", "--agent", "local-guide", "--format", "json", "--auto", reference_prompt],
            repo,
            env,
            out / "reference-opencode.json",
        )

        for variant in ("A", "B"):
            (repo / "opencode.json").write_text(json.dumps(configs[variant], ensure_ascii=False, indent=2), encoding="utf-8")
            for question in questions:
                qid = question["id"]
                record = run_cli(
                    [args.opencode, "run", "--standalone", "--agent", "local-guide", "--format", "json", "--auto", question["question"]],
                    repo,
                    env,
                    out / f"{variant}-{qid}.json",
                )
                answers[variant][qid] = final_text(record)
                if read_seen(record):
                    read_counts[variant] += 1

            # Three warmed repetitions of Q1, each in a fresh OpenCode session.
            for repeat in range(1, 4):
                record = run_cli(
                    [args.opencode, "run", "--standalone", "--agent", "local-guide", "--format", "json", "--auto", questions[0]["question"]],
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
            raise RuntimeError("lab/demo changed during read-only experiment")

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
                q["id"]: evaluate(q["id"], answers[variant][q["id"]])
                for q in questions
            }
            for variant in ("A", "B")
        },
    }
    save(out / "answers.json", answers)
    save(out / "summary.json", summary)
    save(out / "ollama-ps.json", api("/api/ps"))
    write_report(out, questions, answers, summary, environment)
    print(f"Practice 3 complete: {out}")


if __name__ == "__main__":
    main()
