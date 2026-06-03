from app.services.storage_service import _folder_path


def test_imagekit_folder_path_uses_ayati_admin_base_folder():
    assert _folder_path("images") == "/ayati-admin/images"


def test_imagekit_folder_path_maps_profile_and_document_categories():
    assert _folder_path("avatars") == "/ayati-admin/profile"
    assert _folder_path("profile") == "/ayati-admin/profile"
    assert _folder_path("files") == "/ayati-admin/documents"
    assert _folder_path("documents") == "/ayati-admin/documents"
