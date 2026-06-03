from app.core.permissions import get_all_permissions


def test_permission_management_codes_exist_in_catalog():
    permissions = {permission["code"] for permission in get_all_permissions()}

    assert "permission.view" in permissions
    assert "permission.create" in permissions
    assert "permission.edit" in permissions
    assert "permission.delete" in permissions
    assert "bot.view" in permissions
    assert "bot.create" in permissions
    assert "bot.edit" in permissions
    assert "bot.delete" in permissions
    assert "announcement.create" in permissions
