from crewai_tools import FileReadTool, FileWriterTool, JSONSearchTool

# Ferramentas padrão do framework com nomes customizados
file_read_tool = FileReadTool(
    name="search_a_files_content",
    description="Search and read content from files in the project"
)
file_write_tool = FileWriterTool(
    name="write_to_file", 
    description="Write content to files"
)
json_search_tool = JSONSearchTool(
    name="search_a_json_content",
    description="Search and read JSON files"
)
