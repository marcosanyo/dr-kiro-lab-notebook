"""Unit tests for the solver-file extractors (wind-tunnel design 9, Requirement 13.1, 13.2)."""

from pathlib import Path

import pytest

from bench.scan.terms import EXTRACTORS, ScanError

DICT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    object      fvSchemes;
}
// a comment with hiddenword
/* block comment blockhidden */
ddtSchemes { default steadyState; }
divSchemes
{
    div(phi,U)  bounded Gauss linearUpwind grad(U);
}
boundaryField
{
    inletPatch { type fixedValue; value uniform (1 0 0); inGroup yes; relax 0.7; }
}
functions { probeSet { type forceCoeffs; log on; rho @RHO_NAME@; } }
"""


def names(extractor: str, tmp_path: Path, text: str, file_name: str = "source") -> list[str]:
    path = tmp_path / file_name
    path.write_text(text, encoding="utf-8")
    return EXTRACTORS[extractor](path)


def test_foam_dictionary_keywords_names_and_values(tmp_path):
    found = names("openfoam-dict", tmp_path, DICT)
    for expected in (
        "ddtSchemes",
        "default",
        "steadyState",
        "divSchemes",
        "linearUpwind",
        "inletPatch",  # a patch name
        "fixedValue",
        "probeSet",  # a function-object name
        "forceCoeffs",
        "RHO_NAME",  # the placeholder @RHO_NAME@
    ):
        assert expected in found


def test_foam_syntax_words_are_left_out(tmp_path):
    found = names("openfoam-dict", tmp_path, DICT)
    for syntax in ("FoamFile", "version", "format", "ascii", "fvSchemes", "yes", "on", "0.7", "1", "0"):
        assert syntax not in found
    assert "hiddenword" not in found and "blockhidden" not in found
    assert "@RHO_NAME@" not in found


def test_foam_unparsable_files_name_the_file(tmp_path):
    for text in ("a { b 1;", "a b ) ;", "a /* open", 'a "open;'):
        with pytest.raises(ScanError, match="source"):
            names("openfoam-dict", tmp_path, text)


def test_shell_command_names_only(tmp_path):
    text = (
        "#!/bin/sh\n"
        "# runHidden is a comment\n"
        'cd "${0%/*}" || exit 1\n'
        ". $WM_PROJECT_DIR/bin/tools/RunFunctions\n"
        "MODE=fast\n"
        "runApplication gridMaker -overwrite\n"
        "if [ -d processor0 ]; then\n"
        "    runParallel solverRunner -parallel\n"
        "fi\n"
        "for t in a b; do postWriter $t; done\n"
    )
    found = names("shell-words", tmp_path, text, "Allrun")
    for expected in ("runApplication", "gridMaker", "runParallel", "solverRunner", "postWriter"):
        assert expected in found
    for left_out in ("if", "then", "fi", "for", "do", "done", "runHidden", "-overwrite", "MODE=fast", "t"):
        assert left_out not in found


def test_shell_unparsable_file(tmp_path):
    with pytest.raises(ScanError, match="Allrun"):
        names("shell-words", tmp_path, "echo 'open\n", "Allrun")


def test_toml_keys_and_name_like_values(tmp_path):
    text = (
        "[image]\n"
        'name = "vendor/flowbox@sha256:' + "ab" * 32 + '"\n'
        'tag = "v2406"\n'
        'note = "this is a sentence, not a name"\n'
        "[[patch]]\n"
        'label = "frontPlate"\n'
        "count = 3\n"
    )
    found = names("toml-names", tmp_path, text, "settings.toml")
    for expected in ("image", "name", "tag", "vendor/flowbox", "v2406", "patch", "label", "frontPlate"):
        assert expected in found
    assert not any("sha256" in n or "abab" in n or "sentence" in n for n in found)


def test_toml_unparsable_file(tmp_path):
    with pytest.raises(ScanError, match="settings.toml"):
        names("toml-names", tmp_path, "key = \n", "settings.toml")


def test_python_names(tmp_path):
    text = (
        '"""A module docstring that is a sentence."""\n'
        "__all__ = ['x']\n"
        "GRID_LAYERS = 4\n"
        "def build_outline(corner):\n"
        "    return 'outlineGroup'\n"
        "class SurfaceMaker:\n"
        "    def make_surface(self):\n"
        "        return 'two words'\n"
    )
    found = names("python-names", tmp_path, text, "geometry.py")
    for expected in ("build_outline", "SurfaceMaker", "make_surface", "GRID_LAYERS", "outlineGroup"):
        assert expected in found
    assert "__all__" not in found and "two words" not in found
    assert "corner" not in found  # parameters are not listed in the design


def test_python_unparsable_file(tmp_path):
    with pytest.raises(ScanError, match="geometry.py"):
        names("python-names", tmp_path, "def (:\n", "geometry.py")


@pytest.mark.parametrize("extractor", ["openfoam-dict", "shell-words", "toml-names", "python-names"])
def test_missing_or_empty_file_is_an_error(extractor, tmp_path):
    with pytest.raises(ScanError, match="missing"):
        EXTRACTORS[extractor](tmp_path / "missing")
    with pytest.raises(ScanError, match="empty"):
        names(extractor, tmp_path, "", "empty")
