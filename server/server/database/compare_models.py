# compare_models.py
from tables import Material, Assemble, Process, Bom, AbnormalCause
from p_tables import P_Material, P_Assemble, P_Process, P_Bom, P_AbnormalCause

def dump_model(cls):
    cols = {}
    for c in cls.__table__.columns:
        cols[c.name] = {
            "type": str(c.type),
            "nullable": c.nullable,
            "default": str(c.default),
            "server_default": str(c.server_default),
        }
    return cols

def compare(a, b, name_a, name_b):
    print(f"\n=== Compare {name_a} vs {name_b} ===")
    cols_a = dump_model(a)
    cols_b = dump_model(b)

    # 在 a 但不在 b
    only_in_a = cols_a.keys() - cols_b.keys()
    # 在 b 但不在 a
    only_in_b = cols_b.keys() - cols_a.keys()
    # 兩邊都有
    both = cols_a.keys() & cols_b.keys()

    if only_in_a:
        print(f"  欄位只存在於 {name_a}: {sorted(only_in_a)}")
    if only_in_b:
        print(f"  欄位只存在於 {name_b}: {sorted(only_in_b)}")

    for col in sorted(both):
        ca, cb = cols_a[col], cols_b[col]
        diffs = []
        if ca["type"] != cb["type"]:
            diffs.append(f"type: {ca['type']} vs {cb['type']}")
        if ca["nullable"] != cb["nullable"]:
            diffs.append(f"nullable: {ca['nullable']} vs {cb['nullable']}")
        if ca["default"] != cb["default"]:
            diffs.append(f"default: {ca['default']} vs {cb['default']}")
        if ca["server_default"] != cb["server_default"]:
            diffs.append(f"server_default: {ca['server_default']} vs {cb['server_default']}")
        if diffs:
            print(f"  欄位 {col} 不同 -> " + "; ".join(diffs))

if __name__ == "__main__":
    compare(Material, P_Material, "Material", "P_Material")
    compare(Assemble, P_Assemble, "Assemble", "P_Assemble")
    compare(Process, P_Process, "Process", "P_Process")
    compare(Bom, P_Bom, "Bom", "P_Bom")
    compare(AbnormalCause, P_AbnormalCause, "AbnormalCause", "P_AbnormalCause")

