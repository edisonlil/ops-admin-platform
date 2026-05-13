from __future__ import annotations


class AIAssetsError(Exception):
    code = "AI_ASSETS_ERROR"
    status_code = 400


class PromptAssetNotFound(AIAssetsError):
    code = "PROMPT_ASSET_NOT_FOUND"
    status_code = 404


class PromptVersionNotFound(AIAssetsError):
    code = "PROMPT_VERSION_NOT_FOUND"
    status_code = 404


class PromptVersionImmutable(AIAssetsError):
    code = "PROMPT_VERSION_IMMUTABLE"
    status_code = 409


class PromptContractNotFound(AIAssetsError):
    code = "PROMPT_CONTRACT_NOT_FOUND"
    status_code = 404


class PromptBindingNotFound(AIAssetsError):
    code = "PROMPT_BINDING_NOT_FOUND"
    status_code = 404


class PromptCompatibilityError(AIAssetsError):
    code = "PROMPT_CONTRACT_INCOMPATIBLE"
    status_code = 422


class PromptRenderError(AIAssetsError):
    code = "PROMPT_RENDER_ERROR"
    status_code = 422


class PromptRunNotFound(AIAssetsError):
    code = "PROMPT_RUN_NOT_FOUND"
    status_code = 404
