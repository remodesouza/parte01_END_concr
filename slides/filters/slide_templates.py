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

CAROUSEL_SCRIPT = """<script>
    (function () {
        if (window.__tplRevealCarouselInit) {
            return;
        }
        window.__tplRevealCarouselInit = true;

        function getCarousel(carousel) {
            return carousel && carousel.querySelectorAll('.tpl-carousel-item').length ? carousel : null;
        }

        function getActiveIndex(carousel) {
            var activeItem = carousel.querySelector('.tpl-carousel-item.is-active');
            if (!activeItem) {
                return 0;
            }

            var items = Array.from(carousel.querySelectorAll('.tpl-carousel-item'));
            var index = items.indexOf(activeItem);
            return index < 0 ? 0 : index;
        }

        function setActiveIndex(carousel, newIndex) {
            carousel = getCarousel(carousel);
            if (!carousel) {
                return;
            }

            var items = carousel.querySelectorAll('.tpl-carousel-item');
            var captions = carousel.querySelectorAll('.tpl-carousel-caption');
            var dots = carousel.querySelectorAll('.tpl-carousel-dot');

            for (var i = 0; i < items.length; i++) {
                var active = i === newIndex;
                items[i].classList.toggle('is-active', active);
                items[i].classList.toggle('is-hidden', !active);
            }

            for (var j = 0; j < captions.length; j++) {
                var captionActive = j === newIndex;
                captions[j].classList.toggle('is-active', captionActive);
                captions[j].classList.toggle('is-hidden', !captionActive);
            }

            for (var k = 0; k < dots.length; k++) {
                dots[k].classList.toggle('is-active', k === newIndex);
            }
        }

        function moveCarousel(carousel, direction) {
            carousel = getCarousel(carousel);
            if (!carousel) {
                return false;
            }

            var items = carousel.querySelectorAll('.tpl-carousel-item');
            var currentIndex = getActiveIndex(carousel);
            var newIndex = currentIndex;

            if (direction === 'prev') {
                newIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
            }
            else if (direction === 'next') {
                newIndex = currentIndex === items.length - 1 ? 0 : currentIndex + 1;
            }

            setActiveIndex(carousel, newIndex);
            return true;
        }

        function bindKeyboardBindings() {
            if (typeof Reveal === 'undefined' || typeof Reveal.addKeyBinding !== 'function') {
                return;
            }

            Reveal.addKeyBinding({ keyCode: 37, key: 'Left', description: 'Previous carousel image' }, function () {
                var currentSlide = Reveal.getCurrentSlide();
                var carousel = currentSlide ? currentSlide.querySelector('.tpl-carousel') : null;
                if (!moveCarousel(carousel, 'prev') && typeof Reveal.prev === 'function') {
                    Reveal.prev();
                }
            });

            Reveal.addKeyBinding({ keyCode: 39, key: 'Right', description: 'Next carousel image' }, function () {
                var currentSlide = Reveal.getCurrentSlide();
                var carousel = currentSlide ? currentSlide.querySelector('.tpl-carousel') : null;
                if (!moveCarousel(carousel, 'next') && typeof Reveal.next === 'function') {
                    Reveal.next();
                }
            });
        }

        document.addEventListener('click', function (event) {
            var button = event.target.closest('[data-carousel-nav]');
            if (!button) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            moveCarousel(button.closest('.tpl-carousel'), button.getAttribute('data-carousel-nav'));
        });

        document.addEventListener('slidechanged', function (event) {
            var slide = event.currentSlide || document;
            slide.querySelectorAll('.tpl-carousel[data-carousel]').forEach(function (carousel) {
                setActiveIndex(carousel, 0);
            });
        });

        window.addEventListener('load', bindKeyboardBindings, { once: true });

        document.querySelectorAll('.tpl-carousel[data-carousel]').forEach(function (carousel) {
            setActiveIndex(carousel, 0);
        });
    })();
</script>"""


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


def parse_bool(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def normalize_alt_and_caption(alt: str, caption: str) -> tuple[str, str]:
    alt = alt or caption or ""
    caption = caption or alt or ""
    return alt, caption


def collect_images(attrs: dict[str, str]) -> list[tuple[str, str, str]]:
    images: list[tuple[str, str, str]] = []

    img1 = attrs.get("img", "")
    if img1:
        alt, caption = normalize_alt_and_caption(attrs.get("alt", ""), attrs.get("caption", ""))
        images.append((img1, alt, caption))

    indexed: list[int] = []
    for key in attrs:
        if key.startswith("img") and key[3:].isdigit():
            indexed.append(int(key[3:]))

    for idx in sorted(set(indexed)):
        img = attrs.get(f"img{idx}", "")
        if img:
            alt, caption = normalize_alt_and_caption(attrs.get(f"alt{idx}", ""), attrs.get(f"caption{idx}", ""))
            images.append((img, alt, caption))

    return images


def render_image_figure(img: str, alt: str, classes: str, width: str, extra_attrs: str = "") -> str:
    attrs = f' class="{classes}"' if classes else ""
    safe_img = html.escape(img, quote=True)
    safe_alt = html.escape(alt, quote=True)
    safe_width = html.escape(width, quote=True)
    return "\n".join(
        [
            f"    <figure{attrs}{extra_attrs}>",
            f'      <img src="{safe_img}" alt="{safe_alt}" style="width: {safe_width};" />',
            "    </figure>",
        ]
    )


def build_image_carousel(images: list[tuple[str, str, str]]) -> str:
    if not images:
        return ""

    has_multiple = len(images) > 1
    html_parts: list[str] = ['<div class="tpl-carousel tpl-carousel-reveal" data-carousel>']
    if has_multiple:
        html_parts.append('  <button type="button" class="tpl-carousel-nav tpl-carousel-prev" data-carousel-nav="prev" aria-label="Previous image">&#10094;</button>')
        html_parts.append('  <button type="button" class="tpl-carousel-nav tpl-carousel-next" data-carousel-nav="next" aria-label="Next image">&#10095;</button>')
    html_parts.append('  <div class="tpl-carousel-viewport">')

    for idx, (img, alt, caption) in enumerate(images):
        visibility_class = "is-active" if idx == 0 else "is-hidden"
        html_parts.append(
            render_image_figure(
                img,
                alt,
                f"tpl-carousel-item {visibility_class}",
                "100%",
                f' data-carousel-index="{idx}"',
            )
        )

    html_parts.append("  </div>")
    html_parts.append('  <div class="tpl-carousel-caption-zone">')

    for idx, (_img, _alt, caption) in enumerate(images):
        safe_caption = html.escape(caption or "")
        visibility_class = "is-active" if idx == 0 else "is-hidden"
        html_parts.append(
            f'    <p class="tpl-carousel-caption {visibility_class}" data-carousel-index="{idx}">{safe_caption}</p>'
        )

    html_parts.append("  </div>")
    html_parts.append('  <div class="tpl-carousel-dots" aria-hidden="true">')
    for idx in range(len(images)):
        active_class = " is-active" if idx == 0 else ""
        html_parts.append(
            f'    <span class="tpl-carousel-dot{active_class}" data-carousel-dot="{idx}"></span>'
        )
    html_parts.append("  </div>")
    html_parts.append("</div>")

    return "\n".join(html_parts)


def build_fragment_images(images: list[tuple[str, str, str]]) -> str:
    html_parts: list[str] = []
    for img, alt, caption in images:
        figure_html = render_image_figure(img, alt, "fragment", "92%").replace("    <figure", "<figure", 1)
        figure_html = figure_html.replace("      <img", "  <img", 1)
        figure_html = figure_html.replace("    </figure>", "</figure>", 1)
        safe_caption = html.escape(caption or "")
        html_parts.append(
            figure_html.replace(
                "</figure>",
                f"  <figcaption>{safe_caption}</figcaption>\n</figure>",
                1,
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


def build_carousel_script(attrs: dict[str, str]) -> str:
    if not parse_bool(attrs.get("carousel", "")):
        return ""
    return CAROUSEL_SCRIPT


def build_texto_carrossel_values(attrs: dict[str, str], content: list[pf.Element]) -> dict[str, str]:
    return {
        "title": attrs.get("title", ""),
        "subtitle": attrs.get("subtitle", ""),
        "body_html": blocks_to_html(content),
        "images_html": build_imagem_ampla_images(attrs),
        "carousel_script": build_carousel_script(attrs),
    }


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

    if "tpl-divider" in el.classes:
        return render_div(
            "tpl-divider.html",
            {
                "title": attrs.get("title", ""),
                "subtitle": attrs.get("subtitle", ""),
                "text": attrs.get("text", ""),
            },
        )

    if "tpl-text" in el.classes:
        return render_div(
            "tpl-text.html",
            {
                "title": attrs.get("title", ""),
                "subtitle": attrs.get("subtitle", ""),
                "body_html": blocks_to_html(list(el.content)),
            },
        )

    if "tpl-text-image" in el.classes:
        return render_div(
            "tpl-text-image.html",
            {
                "title": attrs.get("title", ""),
                "img": attrs.get("img", ""),
                "alt": attrs.get("alt", ""),
                "caption": attrs.get("caption", ""),
                "body_html": blocks_to_html(list(el.content)),
            },
        )

    if "tpl-wide-image" in el.classes:
        return render_div(
            "tpl-wide-image.html",
            {
                "title": attrs.get("title", ""),
                "images_html": build_imagem_ampla_images(attrs),
                "carousel_script": build_carousel_script(attrs),
            },
        )

    if "tpl-text-carousel" in el.classes:
        return render_div(
            "tpl-text-carousel.html",
            build_texto_carrossel_values(attrs, list(el.content)),
        )

    if "tpl-text-table" in el.classes:
        table_html = md_to_html(read_table_source(attrs))
        return render_div(
            "tpl-text-table.html",
            {
                "title": attrs.get("title", ""),
                "caption": attrs.get("caption", ""),
                "body_html": blocks_to_html(list(el.content)),
                "table_html": table_html,
            },
        )

    if "tpl-wide-table" in el.classes:
        table_html = md_to_html(read_table_source(attrs))
        return render_div(
            "tpl-wide-table.html",
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
