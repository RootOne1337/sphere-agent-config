#!/usr/bin/env python3
"""
generate_device_config.py — генератор sphere-agent-config.json для массового деплоя.

Использование:
  # Один конфиг для LDPlayer клона
  python generate_device_config.py \
    --env development \
    --workstation-id ws-PC-FARM-01 \
    --instance-index 42 \
    --location msk-office-1

  # Batch: 30 конфигов для одной воркстанции
  python generate_device_config.py \
    --env development \
    --workstation-id ws-PC-FARM-01 \
    --count 30 \
    --start-index 0 \
    --location msk-office-1 \
    --output-dir ./output

"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


# Корень agent-config относительно скрипта
CONFIG_ROOT = Path(__file__).resolve().parent.parent


def load_environment(env_name: str) -> dict:
    """Загрузить конфигурацию окружения."""
    env_file = CONFIG_ROOT / "environments" / f"{env_name}.json"
    if not env_file.exists():
        print(f"Ошибка: окружение '{env_name}' не найдено ({env_file})", file=sys.stderr)
        sys.exit(1)
    with open(env_file, encoding="utf-8") as f:
        return json.load(f)


def load_schema() -> dict:
    """Загрузить JSON Schema для валидации."""
    schema_file = CONFIG_ROOT / "schema.json"
    if not schema_file.exists():
        raise FileNotFoundError(f"JSON Schema не найдена: {schema_file}")
    with open(schema_file, encoding="utf-8") as f:
        return json.load(f)


def validate_config(config: dict, schema: dict) -> list[str]:
    """Validate fields used by the legacy generator without exposing secrets."""
    errors: list[str] = []
    if not isinstance(config, dict):
        return ["Конфигурация должна быть JSON-объектом"]

    required = schema.get("required", [])
    for field in required:
        if field not in config or config[field] is None:
            errors.append(f"Обязательное поле '{field}' отсутствует или null")

    version = config.get("config_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append("config_version должен быть положительным целым числом")

    server_url = config.get("server_url")
    if not isinstance(server_url, str) or not server_url.strip():
        errors.append("server_url отсутствует; задайте SPHERE_SERVER_URL с проверенным адресом")
    else:
        try:
            parsed_url = urlsplit(server_url)
            valid_host = bool(parsed_url.hostname)
        except ValueError:
            parsed_url = None
            valid_host = False
        if parsed_url is None or parsed_url.scheme not in {"http", "https"} or not valid_host:
            errors.append("server_url должен быть абсолютным HTTP(S) URL")
        elif parsed_url.username or parsed_url.password or parsed_url.fragment:
            errors.append("server_url не должен содержать учётные данные или fragment")
        elif config.get("environment") in {"production", "staging"} and parsed_url.scheme != "https":
            errors.append("Для production и staging требуется HTTPS")

    environment = config.get("environment")
    if environment not in {"production", "staging", "development"}:
        errors.append("environment должен быть production, staging или development")

    # Never include credential material in a validation message.
    key = config.get("enrollment_api_key", "")
    if not isinstance(key, str) or not key.startswith("sphr_") or len(key) <= len("sphr_"):
        errors.append("enrollment_api_key отсутствует или имеет неверный формат (ожидается префикс sphr_)")

    ws_path = config.get("ws_path", "/ws/android")
    if not isinstance(ws_path, str) or not ws_path.startswith("/") or ws_path.startswith("//"):
        errors.append("ws_path должен быть абсолютным путём внутри API")

    instance_index = config.get("instance_index")
    if instance_index is not None and (
        not isinstance(instance_index, int) or isinstance(instance_index, bool) or instance_index < 0
    ):
        errors.append("instance_index должен быть неотрицательным целым числом или null")

    workstation_id = config.get("workstation_id")
    if workstation_id is not None and (
        not isinstance(workstation_id, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", workstation_id)
    ):
        errors.append("workstation_id должен содержать 1–100 латинских букв, цифр, дефисов или подчёркиваний")

    location = config.get("location")
    if location is not None and (
        not isinstance(location, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", location)
    ):
        errors.append("location должен содержать 1–50 латинских букв, цифр, дефисов или подчёркиваний")

    poll_interval = config.get("config_poll_interval_seconds", 86400)
    if not isinstance(poll_interval, int) or isinstance(poll_interval, bool) or poll_interval < 300:
        errors.append("config_poll_interval_seconds должен быть целым числом не меньше 300")

    features = config.get("features", {})
    if not isinstance(features, dict) or any(
        name not in {"telemetry_enabled", "streaming_enabled", "ota_enabled", "auto_register"}
        or not isinstance(value, bool)
        for name, value in features.items()
    ):
        errors.append("features должен содержать только известные булевы флаги")
    return errors


def generate_single_config(
    env_config: dict,
    workstation_id: str | None = None,
    instance_index: int | None = None,
    location: str | None = None,
    ldplayer_name: str | None = None,
) -> dict:
    """Сгенерировать конфиг для одного устройства на основе окружения."""
    config = {
        "config_version": env_config["config_version"],
        "server_url": env_config["server_url"],
        "ws_path": env_config.get("ws_path", "/ws/android"),
        "enrollment_api_key": env_config["enrollment_api_key"],
        "device_id": None,
        "workstation_id": workstation_id,
        "instance_index": instance_index,
        "location": location or env_config.get("location"),
        "environment": env_config.get("environment", "production"),
        "config_poll_interval_seconds": env_config.get("config_poll_interval_seconds", 86400),
        "features": env_config.get("features", {
            "telemetry_enabled": True,
            "streaming_enabled": True,
            "ota_enabled": True,
            "auto_register": True,
        }),
        "meta": {},
    }
    if ldplayer_name:
        config["meta"]["ldplayer_name"] = ldplayer_name
    if workstation_id and instance_index is not None:
        config["meta"]["clone_source"] = "auto-generated"
    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Генератор sphere-agent-config.json для массового деплоя агентов.",
    )
    parser.add_argument(
        "--env", required=True, choices=["production", "staging", "development"],
        help="Целевое окружение",
    )
    parser.add_argument("--workstation-id", help="ID воркстанции (PC-хоста)")
    parser.add_argument("--instance-index", type=int, help="Индекс LDPlayer инстанса (0-based)")
    parser.add_argument("--location", help="Код локации (msk-office-1)")
    parser.add_argument("--ldplayer-name", help="Имя LDPlayer инстанса")
    parser.add_argument(
        "--count", type=int, default=1,
        help="Количество конфигов (batch-генерация)",
    )
    parser.add_argument(
        "--start-index", type=int, default=0,
        help="Начальный instance_index для batch-генерации",
    )
    parser.add_argument(
        "--output-dir", default="./output",
        help="Директория для сохранения сгенерированных конфигов",
    )
    parser.add_argument(
        "--output-file",
        help="Имя файла (для одного конфига). По умолчанию: sphere-agent-config.json",
    )
    args = parser.parse_args()

    if args.count < 1 or args.count > 10000:
        parser.error("--count должен быть в диапазоне 1..10000")
    if args.count > 1 and not args.workstation_id:
        parser.error("для batch-генерации требуется --workstation-id, чтобы вычислить уникальные индексы")
    if args.output_file and (
        Path(args.output_file).name != args.output_file
        or "/" in args.output_file
        or "\\" in args.output_file
    ):
        parser.error("--output-file должен быть именем файла без пути")

    # Загружаем окружение и схему
    env_config = load_environment(args.env)
    server_url = os.environ.get("SPHERE_SERVER_URL", "").strip()
    enrollment_key = os.environ.get("SPHERE_ENROLLMENT_API_KEY", "").strip()
    if server_url:
        env_config["server_url"] = server_url
    env_config["enrollment_api_key"] = enrollment_key
    schema = load_schema()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for i in range(args.count):
        if args.workstation_id:
            idx = args.start_index + i if args.count > 1 else (
                args.instance_index if args.instance_index is not None else args.start_index
            )
        else:
            idx = args.instance_index
        name = args.ldplayer_name
        if args.count > 1:
            name = name or f"Farm-{idx:03d}"

        config = generate_single_config(
            env_config=env_config,
            workstation_id=args.workstation_id,
            instance_index=idx,
            location=args.location,
            ldplayer_name=name,
        )

        # Валидация
        errors = validate_config(config, schema)
        if errors:
            print(f"Ошибки валидации конфига #{i}:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            sys.exit(1)

        # Имя файла
        if args.count == 1:
            filename = args.output_file or "sphere-agent-config.json"
        else:
            filename = f"sphere-agent-config-{idx:03d}.json"

        filepath = output_dir / filename
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=filepath.parent,
                prefix=f".{filepath.name}.",
                suffix=".tmp",
                delete=False,
            ) as f:
                temporary_path = Path(f.name)
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(temporary_path, filepath)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        generated += 1

    print(f"Сгенерировано конфигов: {generated}")
    print(f"Директория: {output_dir.resolve()}")
    if args.count == 1:
        filename = args.output_file or "sphere-agent-config.json"
        print(f"\nФайл содержит enrollment credential; ограничьте доступ: {output_dir / filename}")
    else:
        print(f"\nФайлы содержат enrollment credentials; ограничьте доступ к {output_dir.resolve()}")


if __name__ == "__main__":
    main()
