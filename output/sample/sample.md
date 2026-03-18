# **Sample Technical Document**

This is a sample PDF used to demonstrate the pdfToMarkdown converter. It contains common document elements that the converter handles: headings, paragraphs, tables, lists, and formatted text.

### **Overview**

The pdfToMarkdown tool converts PDF files into well-structured Markdown suitable for AI agent consumption. It uses GPU-accelerated layout detection, OCR, and table recognition via the marker-pdf library.

## **Supported Elements**

- **Headings** H1 through H6, with proper hierarchy •
- **Paragraphs** plain text with inline formatting •
- **Tables** converted to Markdown table syntax •
- **Lists** ordered and unordered •
- **Images** extracted and saved alongside the Markdown •
- **Code blocks** preserved with monospace formatting •

## **System Requirements**

| Component | Minimum               | Recommended            |
|-----------|-----------------------|------------------------|
| GPU       | NVIDIA with 8GB VRAM  | NVIDIA with 24GB+ VRAM |
| CUDA      | 11.8                  | 12.0+                  |
| RAM       | 16 GB                 | 32 GB+                 |
| Python    | 3.10                  | 3.12+                  |
| OS        | Linux (Ubuntu 20.04+) | Ubuntu 22.04           |

#### **Quick Start**

To convert a folder of PDFs:

- Place your PDF files in the PDFs/ folder 1.
- Run python convert.py PDFs/ -o output/ 2.
- Retrieve results from the output/ folder 3.

**Note:** The first run will download ML models (~2GB) to ~/.cache/ datalab/models/ . Subsequent runs will reuse these cached models.

#### **Performance Notes**

Conversion speed scales with GPU capability. On an NVIDIA RTX Pro 6000 Blackwell (96GB VRAM), a 100-page technical document converts in approximately 15-20 seconds. Larger documents with 1,000+ pages may take 5-10 minutes depending on content complexity, number of tables, and image density.