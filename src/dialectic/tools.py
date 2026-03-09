from crewai_tools import (
    FileReadTool,
    FileWriterTool,
    JSONSearchTool,
    DirectoryReadTool,
    CodeDocsSearchTool,
)

file_read_tool = FileReadTool(
    name="search_a_files_content",
    description="Search and read content from files in the project",
)
file_write_tool = FileWriterTool(
    name="write_to_file",
    description="Write content to files",
)

directory_read_tool = DirectoryReadTool(
    name="list_directory",
    description="List contents of a directory to understand project structure",
)

try:
    json_search_tool = JSONSearchTool(
        name="search_a_json_content",
        description="Search and read JSON files",
    )
except Exception:
    json_search_tool = None

try:
    code_docs_tool = CodeDocsSearchTool(
        name="search_code_docs",
        description="Search through code documentation and technical documents",
    )
except Exception:
    code_docs_tool = None
