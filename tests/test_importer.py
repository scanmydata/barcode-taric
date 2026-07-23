from barcodetaric.taric import importer


def test_parse_csv(tmp_path):
    path = tmp_path / "cn.csv"
    path.write_text(
        "CN Code,EN,EL\n"
        "0901,Coffee,Καφές\n"
        "2201,Waters,Νερά\n"
        "6109,T-shirts,Μπλουζάκια\n",
        encoding="utf-8",
    )
    rows = importer.parse_file(path, "test")
    codes = {r.code for r in rows}
    assert {"0901", "2201", "6109"} <= codes
    coffee = next(r for r in rows if r.code == "0901")
    assert coffee.description_en == "Coffee"
    assert coffee.description_el == "Καφές"
    assert coffee.hs4 == "0901"


def test_parse_csv_single_desc_lang_detect(tmp_path):
    path = tmp_path / "cn2.csv"
    path.write_text("code,description\n1806,Σοκολάτα\n8471,Computers\n", encoding="utf-8")
    rows = importer.parse_file(path, "t")
    choc = next(r for r in rows if r.code == "1806")
    comp = next(r for r in rows if r.code == "8471")
    assert choc.description_el == "Σοκολάτα"
    assert comp.description_en == "Computers"
