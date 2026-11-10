from app.models.warehouse import Warehouse


def test_warehouse_table_definition() -> None:
    table = Warehouse.__table__

    assert table.name == "warehouses"
    assert set(table.columns.keys()) == {
        "id",
        "warehouse_code",
        "name",
        "created_at",
    }
    assert table.c.id.primary_key
    assert table.c.warehouse_code.unique
    assert not table.c.warehouse_code.nullable
    assert not table.c.name.nullable
    assert table.c.created_at.type.timezone is True
