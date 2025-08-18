import os
import sys
import logging
import anyio
import subprocess
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def convert_markdown_to_pdf(args):
    input_md_path = args.get("markdown_path")
    output_pdf_path = args.get("pdf_path")

    if not input_md_path or not output_pdf_path:
        return [types.TextContent(type="text", text="Missing input or output path.")]

    if not os.path.exists(input_md_path):
        return [types.TextContent(type="text", text=f"Markdown file not found: {input_md_path}")]

    try:
        subprocess.run([
            "pandoc",
            input_md_path,
            "-o", output_pdf_path,
            "--pdf-engine=xelatex"
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF conversion failed: {e}")
        return [types.TextContent(type="text", text="PDF conversion failed.")]

    if os.path.exists(output_pdf_path):
        return [types.TextContent(
            type="text",
            text=f"Markdown file converted to PDF.\n\nPDF Path: `{output_pdf_path}`"
        )]
    else:
        return [types.TextContent(type="text", text="Conversion finished but PDF not found.")]

async def _call_tool_handler(name, arguments):
    if name == "markdown_to_pdf":
        return await convert_markdown_to_pdf(arguments)
    raise ValueError(f"Unknown tool: {name}")

async def _list_tools_handler():
    return [types.Tool(
        name="markdown_to_pdf",
        description="Convert a Markdown file to PDF using pandoc",
        inputSchema={
            "type": "object",
            "properties": {
                "markdown_path": {"type": "string"},
                "pdf_path": {"type": "string"}
            },
            "required": ["markdown_path", "pdf_path"]
        }
    )]

def create_server() -> Server:
    app = Server("pdf_export_server")
    app.call_tool()(_call_tool_handler)
    app.list_tools()(_list_tools_handler)
    return app

def main():
    logger.info("Starting PDF Export Server...")
    app = create_server()

    async def run():
        async with stdio_server() as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options()
            )

    anyio.run(run)

if __name__ == "__main__":
    sys.exit(main())

# import os
# import sys
# import logging
# import anyio
# import subprocess
# from mcp.server.lowlevel import Server
# from mcp.server.stdio import stdio_server
# import mcp.types as types
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
# async def convert_markdown_to_pdf(args):
#     input_md_path = args.get("markdown_path")
#     output_pdf_path = args.get("pdf_path")
#
#     if not input_md_path or not output_pdf_path:
#         return [types.TextContent(type="text", text="Missing input or output path.")]
#
#     if not os.path.exists(input_md_path):
#         return [types.TextContent(type="text", text=f"Markdown file not found: {input_md_path}")]
#
#     try:
#         subprocess.run([
#             "pandoc",
#             "--wrap=preserve",
#             input_md_path,
#             "-o", output_pdf_path,
#             "--pdf-engine=xelatex"
#         ], check=True)
#     except subprocess.CalledProcessError as e:
#         logger.error(f"PDF conversion failed: {e}")
#         return [types.TextContent(type="text", text="PDF conversion failed.")]
#
#     if os.path.exists(output_pdf_path):
#         return [types.TextContent(
#             type="text",
#             text=f"Markdown file converted to PDF.\n\nPDF Path: `{output_pdf_path}`"
#         )]
#     else:
#         return [types.TextContent(type="text", text="Conversion finished but PDF not found.")]
#
# async def _call_tool_handler(name, arguments):
#     if name == "markdown_to_pdf":
#         return await convert_markdown_to_pdf(arguments)
#     raise ValueError(f"Unknown tool: {name}")
#
# async def _list_tools_handler():
#     return [types.Tool(
#         name="markdown_to_pdf",
#         description="Convert a Markdown file to PDF using pandoc",
#         inputSchema={
#             "type": "object",
#             "properties": {
#                 "markdown_path": {"type": "string"},
#                 "pdf_path": {"type": "string"}
#             },
#             "required": ["markdown_path", "pdf_path"]
#         }
#     )]
#
# def create_server() -> Server:
#     app = Server("pdf_export_server")
#     app.call_tool()(_call_tool_handler)
#     app.list_tools()(_list_tools_handler)
#     return app
#
# def main():
#     logger.info("Starting PDF Export Server...")
#     app = create_server()
#
#     async def run():
#         async with stdio_server() as streams:
#             await app.run(
#                 streams[0],
#                 streams[1],
#                 app.create_initialization_options()
#             )
#
#     anyio.run(run)
#
# if __name__ == "__main__":
#     sys.exit(main())