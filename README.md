# pdfToMarkdown

GPU-accelerated batch PDF to Markdown converter designed for preparing large document libraries for AI agent consumption. Uses [marker-pdf](https://github.com/VikParuchuri/marker) with NVIDIA CUDA to perform layout detection, OCR, and table recognition locally — no cloud APIs required.

## Features

- **GPU-accelerated** — layout detection, OCR, and table recognition run on your NVIDIA GPU
- **Batch processing** — point at a folder and convert every PDF in one command
- **Single file mode** — convert individual PDFs as needed
- **Image extraction** — diagrams, screenshots, and figures are saved alongside the markdown
- **Table recognition** — tables are converted to proper markdown table syntax
- **Structured output** — each PDF gets its own folder with markdown, images, and metadata
- **Index generation** — an `INDEX.md` is created linking all converted documents
- **Parallel processing** — optional multi-worker mode for systems with VRAM headroom

## Requirements

- Python 3.10+
- NVIDIA GPU with CUDA support (tested on RTX Pro 6000 Blackwell, 96GB VRAM)
- Ubuntu 22.04 or compatible Linux distribution
- ~4-8GB VRAM per worker during conversion

## Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/pdfToMarkdown.git
cd pdfToMarkdown

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install "marker-pdf[full]"
```

On Ubuntu, you may need image library headers for Pillow:

```bash
sudo apt-get install -y libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev \
    libwebp-dev libtiff-dev libharfbuzz-dev libfribidi-dev
```

## Workflow

The intended workflow is:

1. **Add** your PDF files to the `PDFs/` folder
2. **Run** `convert.py` to process them
3. **Retrieve** the results from the `output/` folder

A `sample.pdf` and its converted output are included in the repo so you can see what to expect before processing your own files.

### Convert a folder of PDFs

```bash
source venv/bin/activate
python convert.py PDFs/ -o output/
```

### Convert a single file

```bash
python convert.py PDFs/my-document.pdf -o output/
```

### Use any input/output paths

The tool is not limited to the `PDFs/` and `output/` folders — you can point it at any path:

```bash
python convert.py /path/to/any/folder/ -o /path/to/results/
python convert.py /path/to/single-file.pdf
```

When no `-o` flag is provided, results are written to `<input>_markdown/` next to the source.

## Options

| Flag | Default | Description |
|---|---|---|
| `-o, --output` | `<input>_markdown/` | Output directory |
| `--workers N` | `1` | Parallel PDF conversions (each worker loads its own GPU models) |
| `--batch-size N` | auto | Layout model batch size — higher uses more VRAM but is faster |
| `--dpi N` | `192` | High-resolution DPI for OCR |
| `--no-ocr` | off | Disable OCR (faster, for text-native PDFs only) |

### Performance tuning

```bash
# Faster for text-native PDFs (no scanned pages)
python convert.py PDFs/ -o output/ --no-ocr

# Use more VRAM for faster layout detection
python convert.py PDFs/ -o output/ --batch-size 32

# Higher quality OCR for scanned documents
python convert.py PDFs/ -o output/ --dpi 288
```

## Output structure

```
output/
├── INDEX.md                          # Links to all converted documents
├── sample/
│   ├── sample.md                     # The converted markdown
│   └── metadata.json                 # Source file, timing, image count
├── My Document/
│   ├── My Document.md
│   ├── metadata.json
│   ├── _page_3_Figure_1.jpeg         # Extracted images (if any)
│   └── _page_12_Figure_4.jpeg
└── ...
```

### metadata.json

Each converted document includes a metadata file:

```json
{
  "source_pdf": "/path/to/original.pdf",
  "conversion_time_seconds": 17.8,
  "image_count": 24
}
```

## Repo layout and .gitignore

The `PDFs/` and `output/` folders are gitignored except for the included sample files:

- `PDFs/sample.pdf` — a small reference PDF (tracked)
- `output/sample/` — its converted result (tracked)
- All other files you add to `PDFs/` or generate in `output/` are ignored by git

This keeps the repo clean while letting you use it as a working directory for large-scale conversions.

## Benchmarks

Tested on NVIDIA RTX Pro 6000 Blackwell (96GB VRAM), Ubuntu 22.04:

| Document | Pages | Time | Markdown Size | Images |
|---|---|---|---|---|
| Small technical doc (96 pages) | 96 | 16s | 124 KB | 2 |
| API reference (1,292 pages) | 1,292 | 304s | 1.5 MB | 17 |
| Full product manual (1,325 pages) | 1,325 | 653s | 2.9 MB | 536 |
| 9 PDFs total | ~3,000+ | 17.5 min | — | 712 |

First run downloads ML models (~2GB) to `~/.cache/datalab/models/`. Subsequent runs reuse cached models.

## How it works

The converter uses [marker-pdf](https://github.com/VikParuchuri/marker) which chains several GPU-accelerated models:

1. **Layout detection** — identifies headings, paragraphs, tables, figures, lists, and page structure
2. **OCR error detection** — flags text regions that need re-recognition
3. **OCR** (via [surya](https://github.com/VikParuchuri/surya)) — re-recognizes flagged regions and scanned content
4. **Table recognition** — detects table boundaries and cell structure, converts to markdown tables
5. **Rendering** — assembles the final markdown with proper heading hierarchy, lists, and image references

## License

MIT
