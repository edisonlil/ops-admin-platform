from __future__ import annotations


class FileManagementError(Exception):
    code = "FILE_MANAGEMENT_ERROR"
    status_code = 400


class FileLibraryNotFound(FileManagementError):
    code = "FILE_LIBRARY_NOT_FOUND"
    status_code = 404


class FileLibraryNotEmpty(FileManagementError):
    code = "FILE_LIBRARY_NOT_EMPTY"
    status_code = 409


class FileFolderNotFound(FileManagementError):
    code = "FILE_FOLDER_NOT_FOUND"
    status_code = 404


class FileFolderNotEmpty(FileManagementError):
    code = "FILE_FOLDER_NOT_EMPTY"
    status_code = 409


class FileFolderConflict(FileManagementError):
    code = "FILE_FOLDER_CONFLICT"
    status_code = 409


class ManagedFileNotFound(FileManagementError):
    code = "FILE_NOT_FOUND"
    status_code = 404


class QuotaExceeded(FileManagementError):
    code = "FILE_QUOTA_EXCEEDED"
    status_code = 400


class UnsupportedFileType(FileManagementError):
    code = "FILE_TYPE_UNSUPPORTED"
    status_code = 400


class FilePreviewUnsupported(FileManagementError):
    code = "FILE_PREVIEW_UNSUPPORTED"
    status_code = 415


class PreviewProviderUnsupported(FileManagementError):
    code = "FILE_PREVIEW_PROVIDER_UNSUPPORTED"
    status_code = 400


class StorageProviderUnsupported(FileManagementError):
    code = "FILE_STORAGE_PROVIDER_UNSUPPORTED"
    status_code = 400


class StorageNotConfigured(FileManagementError):
    code = "FILE_STORAGE_NOT_CONFIGURED"
    status_code = 503


class StorageOperationFailed(FileManagementError):
    code = "FILE_STORAGE_OPERATION_FAILED"
    status_code = 503
