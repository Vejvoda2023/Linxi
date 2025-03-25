# 支持的语言代码映射
LANGUAGE_MAPPING = {
    "en": "English",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "ar": "Arabic",
    "pt": "Portuguese"
}

def validate_language_code(lang_code: str) -> bool:
    """验证语言代码是否支持"""
    return lang_code in LANGUAGE_MAPPING