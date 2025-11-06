#!/usr/bin/env python3
"""
Convert Gamma API markdown to HTML for browser-based PDF export.
"""

import sys
from pathlib import Path
import markdown

def convert_markdown_to_html(markdown_file: str, output_html: str):
    """Convert markdown file to styled HTML for PDF printing."""
    
    print(f"📖 Reading markdown file: {markdown_file}")
    
    # Read markdown file
    with open(markdown_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print(f"📝 Converting markdown to HTML...")
    
    # Convert markdown to HTML with extensions
    html_body = markdown.markdown(
        md_content,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.toc',
        ]
    )
    
    # Create full HTML document with print-friendly CSS
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gamma Generate API - Complete Documentation (v1.0 + v0.2)</title>
    <style>
        /* Screen styles */
        @media screen {{
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                color: #24292e;
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
                background-color: #ffffff;
            }}
        }}
        
        /* Print styles */
        @media print {{
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.5;
                color: #000;
                margin: 0;
                padding: 0;
            }}
            
            @page {{
                size: letter;
                margin: 0.75in;
            }}
        }}
        
        /* Common styles */
        h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #000;
            border-bottom: 3px solid #667eea;
            padding-bottom: 12px;
            margin-top: 32px;
            margin-bottom: 20px;
            page-break-after: avoid;
        }}
        
        h2 {{
            font-size: 22px;
            font-weight: 600;
            color: #000;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 10px;
            margin-top: 28px;
            margin-bottom: 16px;
            page-break-after: avoid;
        }}
        
        h3 {{
            font-size: 18px;
            font-weight: 600;
            color: #000;
            margin-top: 24px;
            margin-bottom: 12px;
            page-break-after: avoid;
        }}
        
        h4 {{
            font-size: 16px;
            font-weight: 600;
            margin-top: 20px;
            margin-bottom: 10px;
            page-break-after: avoid;
        }}
        
        h5, h6 {{
            font-size: 14px;
            font-weight: 600;
            margin-top: 16px;
            margin-bottom: 8px;
        }}
        
        p {{
            margin-top: 0;
            margin-bottom: 12px;
        }}
        
        code {{
            background-color: #f6f8fa;
            border-radius: 3px;
            padding: 2px 6px;
            font-family: "SF Mono", Monaco, Consolas, "Courier New", monospace;
            font-size: 85%;
            color: #e83e8c;
        }}
        
        pre {{
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            margin: 16px 0;
            page-break-inside: avoid;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #24292e;
            font-size: 12px;
            border: none;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
            font-size: 13px;
            page-break-inside: avoid;
        }}
        
        th, td {{
            border: 1px solid #dfe2e5;
            padding: 8px 12px;
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
            padding-left: 20px;
            margin-left: 0;
            color: #666;
            background-color: #f8f9ff;
            padding: 16px;
            padding-left: 20px;
            margin: 16px 0;
            border-radius: 4px;
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
            margin-bottom: 12px;
            padding-left: 32px;
        }}
        
        li {{
            margin-bottom: 6px;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #eaecef;
            margin: 32px 0;
        }}
        
        /* Print button (hidden when printing) */
        .print-button {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 24px;
            background-color: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            z-index: 1000;
        }}
        
        .print-button:hover {{
            background-color: #5568d3;
        }}
        
        @media print {{
            .print-button {{
                display: none;
            }}
        }}
        
        /* Table of contents styling */
        #toc {{
            background-color: #f8f9ff;
            border: 1px solid #667eea;
            border-radius: 6px;
            padding: 20px;
            margin: 24px 0;
        }}
        
        #toc ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        
        #toc li {{
            margin-bottom: 8px;
        }}
        
        #toc a {{
            color: #667eea;
        }}
        
        /* Warning boxes */
        blockquote:has(p:first-child:contains("🚧")),
        blockquote:has(p:first-child:contains("⚠️")) {{
            background-color: #fff3cd;
            border-left-color: #ffc107;
        }}
    </style>
</head>
<body>
    <button class="print-button" onclick="window.print()">🖨️ Print to PDF</button>
    
    {html_body}
    
    <script>
        // Instructions for PDF export
        console.log('📄 To save as PDF:');
        console.log('1. Click the Print button above (or Cmd+P / Ctrl+P)');
        console.log('2. Select "Save as PDF" as the printer');
        console.log('3. Click Save');
        console.log('');
        console.log('The document is pre-styled for optimal PDF output!');
    </script>
</body>
</html>
"""
    
    # Write HTML file
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✅ HTML created successfully: {output_html}")
    print(f"📍 Location: {Path(output_html).absolute()}")
    print(f"\n📄 To create PDF:")
    print(f"1. Open {output_html} in your browser")
    print(f"2. Click the 'Print to PDF' button (or press Cmd+P)")
    print(f"3. Select 'Save as PDF'")
    print(f"4. Save as GAMMA_API_COMPLETE_V1_AND_V02.pdf")


if __name__ == "__main__":
    input_md = "/Users/max.jackson/Intercom Analysis Tool /GAMMA_API_COMPLETE_V1_AND_V02.md"
    output_html = "/Users/max.jackson/Intercom Analysis Tool /GAMMA_API_COMPLETE_V1_AND_V02.html"
    
    try:
        convert_markdown_to_html(input_md, output_html)
        print("\n🎉 HTML conversion complete!")
        print(f"\n💡 Opening in browser...")
        
        # Try to open in default browser
        import subprocess
        try:
            subprocess.run(['open', output_html], check=False)
            print(f"✅ Opened in browser")
        except:
            print(f"ℹ️  Manually open: {output_html}")
        
    except Exception as e:
        print(f"\n❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

