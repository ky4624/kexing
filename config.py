class Config:
    def __init__(self):
        # Qwen API 配置
        self.QWEN_API_KEY = "sk-c25848fe33294e78bce41ae057404d35"  # your_api_key_here请替换为您的 Qwen API Key
        self.QWEN_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"  # Qwen API 地址
        
        # Agent 配置
        self.AGENT_NAME = "QAI Scripter"
        self.MAX_QUESTIONS = 7
        self.SUPPORTED_LANGUAGES = ["中文", "英文", "马来文"]
        self.SUPPORTED_DURATIONS = ["10秒", "15秒"]