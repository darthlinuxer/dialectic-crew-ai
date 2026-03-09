from crewai_tools import FileReadTool, FileWriterTool, JSONSearchTool

file_read_tool = FileReadTool(
    name="search_a_files_content",
    description="Search and read content from files in the project"
)
file_write_tool = FileWriterTool(
    name="write_to_file",
    description="Write content to files"
)
try:
    json_search_tool = JSONSearchTool(
        name="search_a_json_content",
        description="Search and read JSON files"
    )
except Exception:
    json_search_tool = None
