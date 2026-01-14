import json
import requests
import re
from typing import Dict, Optional
from config import Config

config = Config()

def get_qwen_response(prompt: str, system_prompt: Optional[str] = None) -> str:
    """调用 Qwen API 获取响应"""
    headers = {
        "Authorization": f"Bearer {config.QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": "qwen-max",
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 2048,
        "response_format": {"type": "text"}
    }
    
    try:
        response = requests.post(config.QWEN_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["output"]["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"调用 Qwen API 时出错：{e}")
        # 返回模拟响应以便测试
        return _get_mock_response(prompt)

def parse_json_response(response: str) -> Dict:
    """解析 JSON 响应"""
    # 尝试从响应中提取 JSON
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    # 如果解析失败，返回默认值
    return {}

def _get_mock_response(prompt: str) -> str:
    """获取模拟响应（用于测试）"""
    if "判断意图类型" in prompt:
        return '{"type": "A"}'
    elif "提取以下字段的值" in prompt:
        # 从用户输入中提取关键词
        if "app" in prompt.lower() or "应用" in prompt:
            return '{"product": "健身APP", "audience": null, "tone": null, "style": null, "language": null, "duration": null}'
        elif "年轻人" in prompt or "学生" in prompt or "上班族" in prompt:
            return '{"product": null, "audience": "年轻人", "tone": null, "style": null, "language": null, "duration": null}'
        elif "专业" in prompt or "科技感" in prompt or "快节奏" in prompt:
            return '{"product": null, "audience": null, "tone": "专业可信", "style": null, "language": null, "duration": null}'
        elif "写实" in prompt or "动画" in prompt or "电影感" in prompt:
            return '{"product": null, "audience": null, "tone": null, "style": "电影感", "language": null, "duration": null}'
        elif "中文" in prompt or "英文" in prompt:
            return '{"product": null, "audience": null, "tone": null, "style": null, "language": "中文", "duration": null}'
        elif "10秒" in prompt:
            return '{"product": null, "audience": null, "tone": null, "style": null, "language": null, "duration": "10秒"}'
        elif "15秒" in prompt:
            return '{"product": null, "audience": null, "tone": null, "style": null, "language": null, "duration": "15秒"}'
        else:
            return '{"product": null, "audience": null, "tone": null, "style": null, "language": null, "duration": null}'
    elif "是否已包含明确的核心功能" in prompt:
        return '{"needs_core_function": true, "reason": "产品描述不够具体"}'
    else:
        # 模拟脚本生成
        return '''[0-2s] 【黑屏白字，低沉男声】
"投资人只看前3页...你的BP撑得住吗？"

[2-5s] 【快速剪辑：CEO熬夜改PPT、被拒邮件特写】
"90%的创业计划书，还没讲清价值就被关掉。"

[5-9s] 【镜头拉远：QAI界面自动生成精美BP，数据流动】
"QAI创业助手——AI 5分钟生成投资人认可的商业计划书。"

[9-12s] 【LOGO墙：红杉、真格等+用户证言弹幕】
"上线3个月，8,327位创始人选择，平均融资提升40%。"

[12-15s] 【CTA按钮放大，二维码浮现，鼓点重音】
"立即扫码，免费生成你的第一份AI BP！🚀"'''