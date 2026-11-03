"""Embed the four offline dashboard assets into flash, without a new partition."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate(output):
    files = [
        ("index.html", "text/html; charset=utf-8"),
        ("style.css", "text/css; charset=utf-8"),
        ("app.mjs", "text/javascript; charset=utf-8"),
        ("control.mjs", "text/javascript; charset=utf-8"),
    ]
    lines = ["#pragma once", "#include <cstddef>", "namespace awcar {"]
    for i, (name, _) in enumerate(files):
        text = (ROOT / "dashboard" / name).read_text(encoding="utf-8")
        if ')AWCAR"' in text:
            raise ValueError("raw string delimiter")
        lines.append(f'static constexpr char asset_{i}[] = R"AWCAR({text})AWCAR";')
    lines += [
        "struct WebAsset {const char* path;const char* mime;const char* data;size_t size;};",
        "static constexpr WebAsset web_assets[] = {",
    ]
    for i, (name, mime) in enumerate(files):
        lines.append(
            f'{{"/{"" if i == 0 else name}","{mime}",asset_{i},sizeof(asset_{i})-1}},'
        )
    lines += ["};", "}"]
    p = Path(output)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines) + "\n"
    if not p.exists() or p.read_text(encoding="utf-8") != content:
        p.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    generate(p.parse_args().output)
