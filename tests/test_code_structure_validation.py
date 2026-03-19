"""Tests for the code structure validation module."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=too-few-public-methods

from unittest.mock import MagicMock, patch

from src.main.self_improve.code_structure import (
    MAX_FILE_LINES,
    MAX_PUBLIC_METHODS,
    StructureValidationResult,
    _count_code_lines,
    _count_dependencies,
    _count_public_methods,
    _extract_classes,
    _is_dataclass_or_model,
    collect_changed_python_files,
    validate_code_structure,
)


class TestCountCodeLines:
    def test_empty_file(self, tmp_path):
        file = tmp_path / "empty.py"
        file.write_text("")
        assert _count_code_lines(file) == 0

    def test_only_comments(self, tmp_path):
        file = tmp_path / "comments.py"
        file.write_text("# Comment 1\n# Comment 2\n")
        assert _count_code_lines(file) == 0

    def test_only_blank_lines(self, tmp_path):
        file = tmp_path / "blank.py"
        file.write_text("\n\n\n")
        assert _count_code_lines(file) == 0

    def test_code_lines(self, tmp_path):
        file = tmp_path / "code.py"
        file.write_text("x = 1\ny = 2\nz = x + y\n")
        assert _count_code_lines(file) == 3

    def test_mixed_content(self, tmp_path):
        file = tmp_path / "mixed.py"
        content = """# Header comment

x = 1  # inline comment
# Another comment

def foo():
    pass
"""
        file.write_text(content)
        lines = _count_code_lines(file)
        assert lines == 3  # x = 1, def foo():, pass


class TestExtractClasses:
    def test_no_classes(self, tmp_path):
        file = tmp_path / "no_class.py"
        file.write_text("x = 1\ndef foo(): pass\n")
        classes = _extract_classes(file)
        assert len(classes) == 0

    def test_one_class(self, tmp_path):
        file = tmp_path / "one_class.py"
        file.write_text("class Foo:\n    pass\n")
        classes = _extract_classes(file)
        assert len(classes) == 1
        assert classes[0].name == "Foo"

    def test_multiple_classes(self, tmp_path):
        file = tmp_path / "multi_class.py"
        file.write_text("class Foo:\n    pass\n\nclass Bar:\n    pass\n")
        classes = _extract_classes(file)
        assert len(classes) == 2

    def test_syntax_error(self, tmp_path):
        file = tmp_path / "syntax_error.py"
        file.write_text("class Foo\n    pass\n")  # Missing colon
        classes = _extract_classes(file)
        assert len(classes) == 0


class TestIsDataclassOrModel:
    def test_dataclass(self, tmp_path):
        file = tmp_path / "dataclass.py"
        content = """
from dataclasses import dataclass

@dataclass
class Foo:
    x: int
"""
        file.write_text(content)
        classes = _extract_classes(file)
        assert len(classes) == 1
        assert _is_dataclass_or_model(classes[0]) is True

    def test_pydantic_model(self, tmp_path):
        file = tmp_path / "model.py"
        content = """
from pydantic import BaseModel

class Foo(BaseModel):
    x: int
"""
        file.write_text(content)
        classes = _extract_classes(file)
        assert len(classes) == 1
        assert _is_dataclass_or_model(classes[0]) is True

    def test_regular_class(self, tmp_path):
        file = tmp_path / "regular.py"
        content = """
class Foo:
    def __init__(self):
        self.x = 1
"""
        file.write_text(content)
        classes = _extract_classes(file)
        assert len(classes) == 1
        assert _is_dataclass_or_model(classes[0]) is False


class TestCountPublicMethods:
    def test_no_methods(self, tmp_path):
        file = tmp_path / "no_methods.py"
        file.write_text("class Foo:\n    x = 1\n")
        classes = _extract_classes(file)
        assert _count_public_methods(classes[0]) == 0

    def test_public_methods(self, tmp_path):
        file = tmp_path / "public.py"
        content = """
class Foo:
    def method1(self): pass
    def method2(self): pass
    def _private(self): pass
    def __dunder__(self): pass
"""
        file.write_text(content)
        classes = _extract_classes(file)
        assert _count_public_methods(classes[0]) == 2  # method1, method2


class TestCountDependencies:
    def test_no_init(self, tmp_path):
        file = tmp_path / "no_init.py"
        file.write_text("class Foo:\n    pass\n")
        classes = _extract_classes(file)
        assert _count_dependencies(classes[0]) == 0

    def test_with_dependencies(self, tmp_path):
        file = tmp_path / "deps.py"
        content = """
class Foo:
    def __init__(self, db: Database, logger: Logger):
        self.db = db
        self.logger = logger
"""
        file.write_text(content)
        classes = _extract_classes(file)
        assert _count_dependencies(classes[0]) == 2


class TestStructureValidationResult:
    def test_add_error_violation(self):
        result = StructureValidationResult()
        result.add_violation("test.py", "rule", "message", severity="error")
        assert result.passed is False
        assert len(result.violations) == 1

    def test_add_warning_violation(self):
        result = StructureValidationResult()
        result.add_violation("test.py", "rule", "message", severity="warning")
        assert result.passed is True  # warnings don't fail
        assert len(result.violations) == 1

    def test_build_summary(self):
        result = StructureValidationResult()
        result.add_violation("a.py", "rule1", "error", severity="error")
        result.add_violation("b.py", "rule2", "warning", severity="warning")
        summary = result.build_summary()
        assert "1 errors" in summary
        assert "1 warnings" in summary


class TestValidateCodeStructure:
    def test_file_exceeds_max_lines(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "big.py"
        lines = ["x = 1\n"] * (MAX_FILE_LINES + 10)
        file.write_text("".join(lines))

        result = validate_code_structure(tmp_path, [file])
        assert result.passed is False
        assert any(v.rule == "max-file-lines" for v in result.violations)

    def test_multiple_classes_per_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "multi.py"
        content = """
class Foo:
    def method(self): pass

class Bar:
    def method(self): pass
"""
        file.write_text(content)

        result = validate_code_structure(tmp_path, [file])
        assert result.passed is False
        assert any(v.rule == "one-class-per-file" for v in result.violations)

    def test_god_class_warning(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "god.py"
        methods = "\n".join(
            [f"    def method{i}(self): pass" for i in range(MAX_PUBLIC_METHODS + 5)]
        )
        content = f"class GodClass:\n{methods}\n"
        file.write_text(content)

        result = validate_code_structure(tmp_path, [file])
        assert result.passed is True  # god class is warning only
        assert any(v.rule == "god-class-methods" for v in result.violations)
        assert all(v.severity == "warning" for v in result.violations)

    def test_code_location_violation(self, tmp_path):
        # File outside src/
        wrong_dir = tmp_path / "lib"
        wrong_dir.mkdir()
        file = wrong_dir / "module.py"
        file.write_text("class Foo:\n    pass\n")

        result = validate_code_structure(tmp_path, [file])
        assert result.passed is False
        assert any(v.rule == "code-location" for v in result.violations)

    def test_test_files_skipped(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "test_module.py"
        lines = ["x = 1\n"] * (MAX_FILE_LINES + 10)
        file.write_text("".join(lines))

        result = validate_code_structure(tmp_path, [file])
        assert result.passed is True  # test files are skipped

    def test_valid_structure(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "good.py"
        content = """
class GoodClass:
    def __init__(self, dep: Dependency):
        self.dep = dep

    def method1(self): pass
    def method2(self): pass
"""
        file.write_text(content)

        result = validate_code_structure(tmp_path, [file])
        assert result.passed is True
        assert len(result.violations) == 0

    def test_check_all_src(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "module.py"
        file.write_text("x = 1\n")

        result = validate_code_structure(tmp_path, check_all_src=True)
        assert result.passed is True

    def test_skips_preexisting_large_file_when_baseline_also_exceeds_limit(
        self, tmp_path, monkeypatch
    ):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "legacy_big.py"
        file.write_text("".join(["x = 1\n"] * (MAX_FILE_LINES + 10)))

        monkeypatch.setattr(
            "src.main.self_improve.code_structure._count_code_lines_at_ref",
            lambda *args, **kwargs: MAX_FILE_LINES + 5,
        )

        result = validate_code_structure(
            tmp_path,
            [file],
            baseline_branch="main",
        )

        assert result.passed is True
        assert not result.violations

    def test_flags_large_file_when_baseline_did_not_exceed_limit(
        self, tmp_path, monkeypatch
    ):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "new_big.py"
        file.write_text("".join(["x = 1\n"] * (MAX_FILE_LINES + 10)))

        monkeypatch.setattr(
            "src.main.self_improve.code_structure._count_code_lines_at_ref",
            lambda *args, **kwargs: MAX_FILE_LINES - 1,
        )

        result = validate_code_structure(
            tmp_path,
            [file],
            baseline_branch="main",
        )

        assert result.passed is False
        assert any(v.rule == "max-file-lines" for v in result.violations)

    def test_skips_preexisting_multi_class_file_when_baseline_also_violates(
        self, tmp_path, monkeypatch
    ):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "legacy_multi.py"
        file.write_text("class Foo:\n    pass\n\nclass Bar:\n    pass\n")

        monkeypatch.setattr(
            "src.main.self_improve.code_structure._count_main_classes_at_ref",
            lambda *args, **kwargs: 2,
        )

        result = validate_code_structure(
            tmp_path,
            [file],
            baseline_branch="main",
        )

        assert result.passed is True
        assert not result.violations

    def test_flags_new_multi_class_file_when_baseline_did_not_violate(
        self, tmp_path, monkeypatch
    ):
        src = tmp_path / "src"
        src.mkdir()
        file = src / "new_multi.py"
        file.write_text("class Foo:\n    pass\n\nclass Bar:\n    pass\n")

        monkeypatch.setattr(
            "src.main.self_improve.code_structure._count_main_classes_at_ref",
            lambda *args, **kwargs: 1,
        )

        result = validate_code_structure(
            tmp_path,
            [file],
            baseline_branch="main",
        )

        assert result.passed is False
        assert any(v.rule == "one-class-per-file" for v in result.violations)


class TestCollectChangedPythonFiles:
    @patch("src.main.self_improve.code_structure.subprocess.run")
    def test_collects_diff_and_status_python_files(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="src/dialectic/agents.py\nsrc/README.md\nlib/tool.py\n",
                stderr="",
            ),
            MagicMock(
                returncode=0,
                stdout=" M src/main/cli/entrypoint.py\n?? tests/test_cli_runtime.py\n",
                stderr="",
            ),
        ]

        files = collect_changed_python_files(tmp_path)

        assert files == [
            tmp_path / "lib/tool.py",
            tmp_path / "src/dialectic/agents.py",
            tmp_path / "src/main/cli/entrypoint.py",
            tmp_path / "tests/test_cli_runtime.py",
        ]

    @patch("src.main.self_improve.code_structure.has_semantic_changes_since_ref")
    @patch("src.main.self_improve.code_structure.subprocess.run")
    def test_collects_only_semantic_python_files_when_requested(
        self,
        mock_run,
        mock_has_semantic_changes,
        tmp_path,
    ):
        (tmp_path / ".git").mkdir()
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="src/format_only.py\nsrc/real_change.py\n",
                stderr="",
            ),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        mock_has_semantic_changes.side_effect = [False, True]

        files = collect_changed_python_files(tmp_path, semantic_only=True)

        assert files == [tmp_path / "src/real_change.py"]

    @patch("src.main.self_improve.code_structure.subprocess.run")
    def test_semantic_changes_include_new_file_missing_from_baseline(
        self,
        mock_run,
        tmp_path,
    ):
        project_root = tmp_path
        (project_root / ".git").mkdir()
        file_path = project_root / "src" / "new_module.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("def meaning_of_life() -> int:\n    return 42\n")

        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="src/new_module.py\n",
                stderr="",
            ),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=128, stdout="", stderr="fatal: path does not exist"),
        ]

        files = collect_changed_python_files(project_root, semantic_only=True)

        assert files == [file_path]

    @patch("src.main.self_improve.code_structure.subprocess.run")
    def test_semantic_changes_exclude_ast_equivalent_formatting_only_diff(
        self,
        mock_run,
        tmp_path,
    ):
        project_root = tmp_path
        (project_root / ".git").mkdir()
        file_path = project_root / "src" / "format_only.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text(
            'def greet(name: str) -> str:\n    return f"Hello, {name}"\n'
        )

        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="src/format_only.py\n",
                stderr="",
            ),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(
                returncode=0,
                stdout=("def greet(name:str)->str:\n    return f'Hello, {name}'\n"),
                stderr="",
            ),
        ]

        files = collect_changed_python_files(project_root, semantic_only=True)

        assert files == []
