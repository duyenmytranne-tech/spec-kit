import os

from g4runner import security


def _case(tmp_path, control_extra=""):
    c = tmp_path / "case"
    (c / "system").mkdir(parents=True)
    (c / "0").mkdir()
    (c / "system" / "controlDict").write_text("solver incompressibleFluid;\n" + control_extra)
    (c / "0" / "U").write_text("internalField uniform (0 0 0);\n")
    return c


def test_clean_case_has_no_blocks(tmp_path):
    c = _case(tmp_path, '// type systemCall;  (a comment is not a call)\nlibs ("libforces.so");\n')
    f = security.scan_case(str(c))
    assert security.blocking(f) == []
    assert any("libforces.so" in x["why"] for x in f)


def test_each_dangerous_construct_blocks(tmp_path):
    cases = {
        "systemCall": "functions { a { type systemCall; executeCalls (\"rm -rf ~\"); } }\n",
        "codeStream": "x #codeStream { code #{ os << 1; #}; };\n",
        "calc": "y #calc \"1+1\";\n",
        "coded": "functions { b { type coded; } }\n",
        "libs path": 'libs ("./evil.so");\n',
        "include abs": '#include "/etc/passwd"\n',
    }
    for name, text in cases.items():
        sub = tmp_path / name.replace(" ", "_")
        sub.mkdir()
        c = _case(sub, text)
        assert security.blocking(security.scan_case(str(c))), name


def test_binary_library_in_case_blocks(tmp_path):
    c = _case(tmp_path)
    (c / "constant" / "lib").mkdir(parents=True)
    (c / "constant" / "lib" / "x.so").write_bytes(b"\x7fELF\x00\x00")
    assert security.blocking(security.scan_case(str(c)))


def test_symlink_outside_blocks(tmp_path):
    c = _case(tmp_path)
    os.symlink("/etc/hostname", c / "system" / "outside")
    assert security.blocking(security.scan_case(str(c)))


def test_operator_switch(monkeypatch):
    monkeypatch.delenv("G4_ALLOW_CODED", raising=False)
    assert not security.allowed_by_operator()
    monkeypatch.setenv("G4_ALLOW_CODED", "1")
    assert security.allowed_by_operator()
