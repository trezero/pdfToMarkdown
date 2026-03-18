#!/usr/bin/env python3
"""
PDF to Markdown Converter — GPU-accelerated batch processing.

Uses marker-pdf with NVIDIA GPU acceleration to convert entire folders
of PDFs into well-formatted markdown suitable for AI agent consumption.

Usage:
    python convert.py ssyPDFdocs/                     # Convert folder, output to ssyPDFdocs_markdown/
    python convert.py ssyPDFdocs/ -o output/           # Custom output directory
    python convert.py ssyPDFdocs/ --workers 4           # Parallel PDF processing
    python convert.py document.pdf                     # Convert single file
    python convert.py ssyPDFdocs/ --batch-size 16       # Larger GPU batch size (more VRAM)
"""

import argparse
import os
import sys
import time
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import torch


def get_device_info():
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        return f"{name} ({vram:.0f}GB VRAM)"
    return "CPU (no GPU detected)"


def convert_single_pdf(args_tuple):
    """Convert a single PDF file. Designed to run in a subprocess."""
    pdf_path, output_dir, layout_batch_size, highres_dpi, disable_ocr = args_tuple

    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.config.parser import ConfigParser
    from marker.output import save_output

    config_dict = {
        "output_format": "markdown",
        "output_dir": str(output_dir),
        "disable_image_extraction": False,
        "paginate_output": False,
        "highres_image_dpi": highres_dpi,
    }

    if layout_batch_size:
        config_dict["layout_batch_size"] = layout_batch_size

    if disable_ocr:
        config_dict["disable_ocr"] = True

    config_parser = ConfigParser(config_dict)
    converter = PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
    )

    start = time.time()
    rendered = converter(str(pdf_path))
    elapsed = time.time() - start

    # Save output
    stem = Path(pdf_path).stem
    out_subdir = output_dir / stem
    out_subdir.mkdir(parents=True, exist_ok=True)

    md_path = out_subdir / f"{stem}.md"
    md_path.write_text(rendered.markdown, encoding="utf-8")

    # Save images
    for img_name, img_data in rendered.images.items():
        img_path = out_subdir / img_name
        img_data.save(str(img_path))

    # Save metadata
    meta = {
        "source_pdf": str(pdf_path),
        "conversion_time_seconds": round(elapsed, 2),
        "image_count": len(rendered.images),
    }
    meta_path = out_subdir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return str(pdf_path), elapsed, len(rendered.images)


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF files to well-formatted Markdown using GPU acceleration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        help="PDF file or directory containing PDF files",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory (default: <input>_markdown/)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel PDF conversions (default: 1, increase if you have VRAM headroom)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Layout model batch size — higher uses more VRAM but is faster (default: auto)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=192,
        help="High-resolution DPI for OCR (default: 192)",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR (faster, for text-native PDFs only)",
    )

    args = parser.parse_args()
    input_path = Path(args.input).resolve()

    # Collect PDF files
    if input_path.is_file():
        if not input_path.suffix.lower() == ".pdf":
            print(f"Error: {input_path} is not a PDF file")
            sys.exit(1)
        pdf_files = [input_path]
    elif input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"Error: No PDF files found in {input_path}")
            sys.exit(1)
    else:
        print(f"Error: {input_path} does not exist")
        sys.exit(1)

    # Output directory
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        if input_path.is_dir():
            output_dir = input_path.parent / f"{input_path.name}_markdown"
        else:
            output_dir = input_path.parent / f"{input_path.stem}_markdown"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"PDF to Markdown Converter")
    print(f"========================")
    print(f"Device:      {get_device_info()}")
    print(f"Input:       {input_path}")
    print(f"Output:      {output_dir}")
    print(f"PDF files:   {len(pdf_files)}")
    print(f"Workers:     {args.workers}")
    print(f"OCR:         {'disabled' if args.no_ocr else 'enabled'}")
    print(f"DPI:         {args.dpi}")
    print()

    total_start = time.time()
    results = []

    if args.workers == 1:
        # Sequential — models loaded once, reused across files
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.config.parser import ConfigParser

        config_dict = {
            "output_format": "markdown",
            "output_dir": str(output_dir),
            "disable_image_extraction": False,
            "paginate_output": False,
            "highres_image_dpi": args.dpi,
        }
        if args.batch_size:
            config_dict["layout_batch_size"] = args.batch_size
        if args.no_ocr:
            config_dict["disable_ocr"] = True

        config_parser = ConfigParser(config_dict)
        artifact_dict = create_model_dict()

        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] Converting: {pdf_path.name}")
            start = time.time()

            # Create a fresh converter per file to avoid stale internal state
            config_parser = ConfigParser(config_dict)
            if i == 1:
                artifact_dict = create_model_dict()
            converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=artifact_dict,
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
            )

            rendered = converter(str(pdf_path))
            elapsed = time.time() - start

            # Save output
            stem = pdf_path.stem
            out_subdir = output_dir / stem
            out_subdir.mkdir(parents=True, exist_ok=True)

            md_path = out_subdir / f"{stem}.md"
            md_path.write_text(rendered.markdown, encoding="utf-8")

            for img_name, img_data in rendered.images.items():
                img_path = out_subdir / img_name
                img_data.save(str(img_path))

            meta = {
                "source_pdf": str(pdf_path),
                "conversion_time_seconds": round(elapsed, 2),
                "image_count": len(rendered.images),
            }
            (out_subdir / "metadata.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8"
            )

            md_size = md_path.stat().st_size / 1024
            print(f"    Done in {elapsed:.1f}s — {md_size:.0f}KB markdown, {len(rendered.images)} images")
            results.append((str(pdf_path), elapsed, len(rendered.images)))
    else:
        # Parallel — each worker loads its own models
        task_args = [
            (pdf, output_dir, args.batch_size, args.dpi, args.no_ocr)
            for pdf in pdf_files
        ]
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(convert_single_pdf, ta): ta[0]
                for ta in task_args
            }
            for i, future in enumerate(as_completed(futures), 1):
                pdf_path = futures[future]
                try:
                    path, elapsed, img_count = future.result()
                    print(f"[{i}/{len(pdf_files)}] {Path(path).name} — {elapsed:.1f}s, {img_count} images")
                    results.append((path, elapsed, img_count))
                except Exception as e:
                    print(f"[{i}/{len(pdf_files)}] FAILED: {Path(pdf_path).name} — {e}")

    total_elapsed = time.time() - total_start

    # Summary
    print()
    print(f"Conversion Complete")
    print(f"===================")
    print(f"Total time:  {total_elapsed:.1f}s")
    print(f"Converted:   {len(results)}/{len(pdf_files)} files")
    if results:
        total_conv = sum(r[1] for r in results)
        print(f"Avg time:    {total_conv / len(results):.1f}s per file")
    print(f"Output:      {output_dir}")

    # Create index file
    index_path = output_dir / "INDEX.md"
    lines = ["# Converted Documents\n\n"]
    for pdf_path, elapsed, img_count in sorted(results):
        stem = Path(pdf_path).stem
        lines.append(f"- [{stem}](./{stem}/{stem}.md) — {img_count} images, {elapsed:.1f}s\n")
    index_path.write_text("".join(lines), encoding="utf-8")
    print(f"Index:       {index_path}")


if __name__ == "__main__":
    main()
