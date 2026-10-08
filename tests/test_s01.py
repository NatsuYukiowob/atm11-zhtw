import json
import zipfile

import common
import s01_extract_mods as s01


def test_kubejs_lang_extracted(tmp_path, monkeypatch, repo):
    mods = tmp_path / "mods"
    mods.mkdir()
    with zipfile.ZipFile(mods / "foo.jar", "w") as z:
        z.writestr("assets/foo/lang/en_us.json", json.dumps({"item.foo.a": "A"}))
    kj = tmp_path / "kubejs/assets/atm/lang"
    kj.mkdir(parents=True)
    (kj / "en_us.json").write_text(json.dumps({"item.atm.x": "Star"}))
    monkeypatch.setattr(s01, "MODS_DIR", mods)
    monkeypatch.setattr(s01, "KUBEJS_DIR", tmp_path / "kubejs")
    monkeypatch.setattr(s01, "WORK", common.WORK)
    s01.main()
    assert common.load_json(common.WORK / "extract/en/atm.json") == {"item.atm.x": "Star"}
    idx = common.load_json(common.WORK / "extract/index.json")
    assert idx["atm"]["jars"] == ["kubejs"] and idx["atm"]["en_keys"] == 1
    assert idx["foo"]["en_keys"] == 1


def test_kubejs_lang_with_bom(tmp_path, monkeypatch, repo):
    (tmp_path / "mods").mkdir()
    kj = tmp_path / "kubejs/assets/kubejs/lang"
    kj.mkdir(parents=True)
    (kj / "en_us.json").write_bytes("﻿".encode() + json.dumps({"item.kubejs.x": "X"}).encode())
    monkeypatch.setattr(s01, "MODS_DIR", tmp_path / "mods")
    monkeypatch.setattr(s01, "KUBEJS_DIR", tmp_path / "kubejs")
    monkeypatch.setattr(s01, "WORK", common.WORK)
    s01.main()
    assert common.load_json(common.WORK / "extract/en/kubejs.json") == {"item.kubejs.x": "X"}
