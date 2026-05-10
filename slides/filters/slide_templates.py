#!/usr/bin/env python3
"""Panflute filter to render custom slide template divs from HTML snippets."""

from __future__ import annotations

import html
from pathlib import Path
import re

import panflute as pf


FILTER_DIR = Path(__file__).resolve().parent
SLIDES_DIR = FILTER_DIR.parent
PROJECT_ROOT = SLIDES_DIR.parent
TEMPLATES_DIR = SLIDES_DIR / "templates"
PLACEHOLDER_RE = re.compile(r"{{[A-Za-z0-9_]+}}")


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def md_to_html(markdown_text: str) -> str:
    if not markdown_text:
        return ""
    return pf.convert_text(markdown_text, input_format="markdown", output_format="html")


def blocks_to_html(blocks: list[pf.Element]) -> str:
    if not blocks:
        return ""
    return pf.convert_text(blocks, input_format="panflute", output_format="revealjs")


def substitute(template: str, values: dict[str, str]) -> str:
    output = template
    for key, value in values.items():
        output = output.replace("{{" + key + "}}", str(value or ""))
    return PLACEHOLDER_RE.sub("", output)


def build_extra_images(attrs: dict[str, str]) -> str:
    html_parts: list[str] = []
    for i in (2, 3):
        img = attrs.get(f"img{i}", "")
        if img:
            alt = attrs.get(f"alt{i}", "")
            caption = attrs.get(f"caption{i}", "")
            html_parts.append(
                "\n".join(
                    [
                        '<figure class="fragment">',
                        f'  <img src="{img}" alt="{alt}" style="width: 92%;" />',
                        f"  <figcaption>{caption}</figcaption>",
                        "</figure>",
                    ]
                )
            )
    return "\n".join(html_parts)


def parse_bool(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def collect_images(attrs: dict[str, str]) -> list[tuple[str, str, str]]:
    images: list[tuple[str, str, str]] = []

    img1 = attrs.get("img", "")
    if img1:
        images.append((img1, attrs.get("alt", ""), attrs.get("caption", "")))

    indexed: list[int] = []
    for key in attrs:
        if key.startswith("img") and key[3:].isdigit():
            indexed.append(int(key[3:]))

    for idx in sorted(set(indexed)):
        img = attrs.get(f"img{idx}", "")
        if img:
            images.append((img, attrs.get(f"alt{idx}", ""), attrs.get(f"caption{idx}", "")))

    return images


def build_image_carousel(images: list[tuple[str, str, str]]) -> str:
    if not images:
        return ""

    html_parts: list[str] = ['<div class="tpl-carousel" data-carousel>']
    html_parts.append('  <button type="button" class="tpl-carousel-arrow tpl-carousel-prev" aria-label="Previous image">&#10094;</button>')
    html_parts.append('  <div class="tpl-carousel-viewport">')

    for idx, (img, alt, caption) in enumerate(images):
        active_class = " is-active" if idx == 0 else ""
        safe_caption = html.escape(caption or "", quote=True)
        html_parts.extend(
            [
                f'    <figure class="tpl-carousel-item{active_class}" data-caption="{safe_caption}">',
                f'      <img src="{img}" alt="{alt}" style="width: 100%;" />',
                "    </figure>",
            ]
        )

    html_parts.append("  </div>")
    html_parts.append('  <button type="button" class="tpl-carousel-arrow tpl-carousel-next" aria-label="Next image">&#10095;</button>')
    html_parts.append('  <div class="tpl-carousel-caption" data-carousel-caption></div>')
    html_parts.append('  <div class="tpl-carousel-dots" aria-hidden="true">')
    for idx in range(len(images)):
        active_class = " is-active" if idx == 0 else ""
        html_parts.append(
            f'    <span class="tpl-carousel-dot{active_class}"></span>'
        )
    html_parts.append("  </div>")
    html_parts.append("</div>")

    return "\n".join(html_parts)


def build_fragment_images(images: list[tuple[str, str, str]]) -> str:
    html_parts: list[str] = []
    for img, alt, caption in images:
        html_parts.append(
            "\n".join(
                [
                    '<figure class="fragment">',
                    f'  <img src="{img}" alt="{alt}" style="width: 92%;" />',
                f"    <figcaption>{caption}</figcaption>",
                    "</figure>",
                ]
            )
        )
    return "\n".join(html_parts)


def build_imagem_ampla_images(attrs: dict[str, str]) -> str:
    images = collect_images(attrs)
    if not images:
        return ""

    if parse_bool(attrs.get("carousel", "")):
        return build_image_carousel(images)

    return build_fragment_images(images)


def load_template(name: str) -> str:
    return read_text_file(TEMPLATES_DIR / name)


def read_table_source(attrs: dict[str, str]) -> str:
    table_file = attrs.get("table_file", "")
    if table_file:
        candidate = Path(table_file)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        return read_text_file(candidate)

    table_md = attrs.get("table_md", "")
    return table_md.replace("\\n", "\n") if table_md else ""


def render_div(template_name: str, values: dict[str, str]) -> pf.RawBlock:
    template = load_template(template_name)
    html = substitute(template, values)
    return pf.RawBlock(html, format="html")


def action(el: pf.Element, doc: pf.Doc) -> pf.Element | None:
    if not isinstance(el, pf.Div):
        return None

    attrs = {k: v for k, v in el.attributes.items()}

    if "tpl-divisor" in el.classes:
        return render_div(
            "tpl-divisor.html",
            {
                "title": attrs.get("title", ""),
                "subtitle": attrs.get("subtitle", ""),
                "text": attrs.get("text", ""),
            },
        )

    if "tpl-texto" in el.classes:
        return render_div(
            "tpl-texto.html",
            {
                "title": attrs.get("title", ""),
                "subtitle": attrs.get("subtitle", ""),
                "body_html": blocks_to_html(list(el.content)),
            },
        )

    if "tpl-texto-imagem" in el.classes:
        return render_div(
            "tpl-texto-imagem.html",
            {
                "title": attrs.get("title", ""),
                "img": attrs.get("img", ""),
                "alt": attrs.get("alt", ""),
                "caption": attrs.get("caption", ""),
                "body_html": blocks_to_html(list(el.content)),
            },
        )

    if "tpl-imagem-ampla" in el.classes:
        return render_div(
            "tpl-imagem-ampla.html",
            {
                "title": attrs.get("title", ""),
                "images_html": build_imagem_ampla_images(attrs),
            },
        )

    if "tpl-texto-tabela" in el.classes:
        table_html = md_to_html(read_table_source(attrs))
        return render_div(
            "tpl-texto-tabela.html",
            {
                "title": attrs.get("title", ""),
                "caption": attrs.get("caption", ""),
                "body_html": blocks_to_html(list(el.content)),
                "table_html": table_html,
            },
        )

    if "tpl-tabela-ampla" in el.classes:
        table_html = md_to_html(read_table_source(attrs))
        return render_div(
            "tpl-tabela-ampla.html",
            {
                "title": attrs.get("title", ""),
                "caption": attrs.get("caption", ""),
                "table_html": table_html,
            },
        )

    return None


def main() -> None:
    pf.run_filter(action)


if __name__ == "__main__":
    main()
