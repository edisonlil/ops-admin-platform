from __future__ import annotations


class AIAssetsError(Exception):
    code = "AI_ASSETS_ERROR"
    status_code = 400


class PromptAssetNotFound(AIAssetsError):
    code = "PROMPT_ASSET_NOT_FOUND"
    status_code = 404


class PromptAssetNameConflict(AIAssetsError):
    code = "PROMPT_ASSET_NAME_CONFLICT"
    status_code = 409


class PromptVersionNotFound(AIAssetsError):
    code = "PROMPT_VERSION_NOT_FOUND"
    status_code = 404


class PromptVersionImmutable(AIAssetsError):
    code = "PROMPT_VERSION_IMMUTABLE"
    status_code = 409


class PromptVersionStateConflict(AIAssetsError):
    code = "PROMPT_VERSION_STATE_CONFLICT"
    status_code = 409
