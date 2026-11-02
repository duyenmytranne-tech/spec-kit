import os

from g4runner import manifest


def _write(root, rel, data=b"x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _case(root):
    _write(root, "system/controlDict", b"solver incompressibleFluid;\n")
    _write(root, "system/fvSolution", b"solvers {}\n")
    _write(root, "0/U", b"internalField uniform (0 0 0);\n")
    _write(root, "constant/polyMesh/owner", b"note \"nCells:8\";\n")
    return root


def test_root_is_deterministic_and_order_free(tmp_path):
    a = _case(tmp_path / "a")
    b = tmp_path / "b"
    for rel in ["constant/polyMesh/owner", "0/U", "system/fvSolution", "system/controlDict"]:
        _write(b, rel, (a / rel).read_bytes())
    assert manifest.build_manifest(str(a))["root"] == manifest.build_manifest(str(b))["root"]


def test_generated_and_macos_files_are_excluded(tmp_path):
    c = _case(tmp_path / "c")
    before = manifest.build_manifest(str(c))
    for rel in ["processor0/0/U", "processors4/x", "postProcessing/forces/0/force.dat", "0.5/U", "100/p",
                "log.foamRun", ".DS_Store", "system/._controlDict", "case.foam", "VTK/a.vtk", "dynamicCode/x"]:
        _write(c, rel, b"generated")
    after = manifest.build_manifest(str(c))
    assert after["root"] == before["root"]
    assert [f[0] for f in after["files"]] == ["0/U", "constant/polyMesh/owner", "system/controlDict", "system/fvSolution"]


def test_single_bit_flip_is_detected(tmp_path):
    c = _case(tmp_path / "c")
    exp = manifest.build_manifest(str(c))
    p = c / "system" / "fvSolution"
    data = bytearray(p.read_bytes())
    data[3] ^= 0x01  # one bit
    p.write_bytes(bytes(data))
    ok, diffs, _ = manifest.verify(str(c), exp)
    assert not ok
    assert diffs == ["changed: system/fvSolution (size 11→11)"]


def test_missing_and_unexpected_files(tmp_path):
    c = _case(tmp_path / "c")
    exp = manifest.build_manifest(str(c))
    os.rename(c / "0" / "U", c / "0" / "V")
    ok, diffs, _ = manifest.verify(str(c), exp)
    assert not ok
    assert "missing: 0/U" in diffs and "unexpected: 0/V" in diffs


def test_symlink_hashed_by_target(tmp_path):
    c = _case(tmp_path / "c")
    os.symlink("controlDict", c / "system" / "link")
    m = manifest.build_manifest(str(c))
    entry = [f for f in m["files"] if f[0] == "system/link"][0]
    assert entry[1] == len("controlDict")
