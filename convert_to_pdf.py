#!/usr/bin/env python3
"""
Convert Gamma API markdown documentation to PDF.
Uses markdown and weasyprint libraries.
"""

import sys
from pathlib import Path
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def convert_markdown_to_pdf(markdown_file: str, output_pdf: str):
    """Convert markdown file to PDF with styling."""
    
    print(f"📖 Reading markdown file: {markdown_file}")
    
    # Read markdown file
    with open(markdown_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print(f"📝 Converting markdown to HTML...")
    
    # Convert markdown to HTML with extensions
    html_content = markdown.markdown(
        md_content,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br'
        ]
    )
    
    # Add CSS styling for better PDF output
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: letter;
                margin: 0.75in;
                @top-right {{
                    content: "Gamma API Documentation";
                    font-size: 9pt;
                    color: #666;
                }}
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 9pt;
                    color: #666;
                }}
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #24292e;
                max-width: 100%;
            }}
            
            h1 {{
                font-size: 24pt;
                font-weight: 700;
                color: #000;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10pt;
                margin-top: 24pt;
                margin-bottom: 16pt;
                page-break-after: avoid;
            }}
            
            h2 {{
                font-size: 18pt;
                font-weight: 600;
                color: #000;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 8pt;
                margin-top: 20pt;
                margin-bottom: 12pt;
                page-break-after: avoid;
            }}
            
            h3 {{
                font-size: 14pt;
                font-weight: 600;
                color: #000;
                margin-top: 16pt;
                margin-bottom: 10pt;
                page-break-after: avoid;
            }}
            
            h4, h5, h6 {{
                font-size: 12pt;
                font-weight: 600;
                margin-top: 12pt;
                margin-bottom: 8pt;
                page-break-after: avoid;
            }}
            
            p {{
                margin-top: 0;
                margin-bottom: 10pt;
            }}
            
            code {{
                background-color: #f6f8fa;
                border-radius: 3px;
                padding: 2pt 4pt;
                font-family: "SF Mono", Monaco, "Courier New", monospace;
                font-size: 9.5pt;
                color: #e83e8c;
            }}
            
            pre {{
                background-color: #f6f8fa;
                border-radius: 5px;
                padding: 12pt;
                overflow-x: auto;
                margin: 12pt 0;
                page-break-inside: avoid;
            }}
            
            pre code {{
                background-color: transparent;
                padding: 0;
                color: #24292e;
                font-size: 9pt;
            }}
            
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 12pt 0;
                page-break-inside: avoid;
            }}
            
            th, td {{
                border: 1px solid #dfe2e5;
                padding: 6pt 10pt;
                text-align: left;
            }}
            
            th {{
                background-color: #f6f8fa;
                font-weight: 600;
            }}
            
            tr:nth-child(even) {{
                background-color: #fafbfc;
            }}
            
            blockquote {{
                border-left: 4px solid #667eea;
                padding-left: 16pt;
                margin-left: 0;
                color: #666;
                background-color: #f8f9ff;
                padding: 12pt;
                margin: 12pt 0;
            }}
            
            a {{
                color: #667eea;
                text-decoration: none;
            }}
            
            a:hover {{
                text-decoration: underline;
            }}
            
            ul, ol {{
                margin-top: 0;
                margin-bottom: 10pt;
                padding-left: 24pt;
            }}
            
            li {{
                margin-bottom: 4pt;
            }}
            
            hr {{
                border: none;
                border-top: 2px solid #eaecef;
                margin: 20pt 0;
            }}
            
            .warning {{
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 5px;
                padding: 12pt;
                margin: 12pt 0;
            }}
            
            /* Prevent orphaned headers */
            h1, h2, h3, h4, h5, h6 {{
                page-break-after: avoid;
            }}
            
            /* Keep code blocks together */
            pre, table {{
                page-break-inside: avoid;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    print(f"🎨 Generating PDF with styling...")
    
    # Create PDF
    font_config = FontConfiguration()
    
    HTML(string=styled_html).write_pdf(
        output_pdf,
        font_config=font_config,
        stylesheets=[CSS(string='@page { size: letter; margin: 0.75in; }')]
    )
    
    print(f"✅ PDF created successfully: {output_pdf}")
    
    # Get file size
    pdf_size = Path(output_pdf).stat().st_size
    pdf_size_mb = pdf_size / (1024 * 1024)
    
    print(f"📄 PDF size: {pdf_size_mb:.2f} MB")
    print(f"📍 Location: {Path(output_pdf).absolute()}")


if __name__ == "__main__":
    # Input and output files
    input_md = "/Users/max.jackson/Intercom Analysis Tool /GAMMA_API_COMPLETE_V1_AND_V02.md"
    output_pdf = "/Users/max.jackson/Intercom Analysis Tool /GAMMA_API_COMPLETE_V1_AND_V02.pdf"
    
    try:
        convert_markdown_to_pdf(input_md, output_pdf)
        print("\n🎉 Conversion complete!")
        
    except Exception as e:
        print(f"\n❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


