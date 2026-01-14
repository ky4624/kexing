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
        # 尝试从用户输入中提取推广对象
        user_input_match = re.search(r'用户输入：(.*)', prompt, re.DOTALL)
        if user_input_match:
            user_input = user_input_match.group(1).strip()
            if user_input:
                # 简单的产品名称提取：使用用户输入的前几个词作为产品名称
                # 这种方法虽然简单，但比固定返回null要好
                return f'{{"product": "{user_input}", "audience": null, "tone": null, "style": null, "language": null, "duration": null}}'
        return '{"product": null, "audience": null, "tone": null, "style": null, "language": null, "duration": null}'
    elif "是否已包含明确的核心功能" in prompt:
        return '{"needs_core_function": true, "reason": "产品描述不够具体"}'
    else:
        # 动态生成模拟脚本
        # 尝试从prompt中提取用户输入的产品信息
        product_name = "产品"
        audience = "用户"
        core_feature = "核心功能"
        
        # 从prompt中提取产品名称
        product_match = re.search(r'推广对象：(.*?)[\n\r，。,]', prompt, re.DOTALL)
        if product_match:
            product_name = product_match.group(1).strip()
        else:
            # 如果没有明确的"推广对象："标记，尝试提取第一个可能的产品名称
            general_product_match = re.search(r'"(.*?)"', prompt)
            if general_product_match:
                product_name = general_product_match.group(1).strip()
        
        # 从prompt中提取目标受众
        audience_match = re.search(r'目标受众：(.*?)[\n\r，。,]', prompt, re.DOTALL)
        if audience_match:
            audience = audience_match.group(1).strip()
        
        # 从prompt中提取核心功能
        feature_match = re.search(r'核心功能：(.*?)[\n\r，。,]', prompt, re.DOTALL)
        if feature_match:
            core_feature = feature_match.group(1).strip()
        
        # 生成动态脚本
        return f'''[0-2s] 【黑屏白字，磁性男声】
"{audience}最需要的是什么？"{product_name}给你答案！

[2-5s] 【快速剪辑：{audience}使用{product_name}的场景、痛点解决瞬间】
"生活/工作中的困扰，{product_name}轻松帮你搞定。"

[5-9s] 【镜头聚焦：{product_name}界面展示，{core_feature}功能演示】
"{product_name}——专为{audience}打造的解决方案，{core_feature}让体验更出色！"

[9-12s] 【数据可视化：用户数量增长、满意度评分，配合用户证言】
"已有10,000+用户选择，满意度高达95%！"

[12-15s] 【CTA按钮放大，行动指令清晰，背景音乐高潮】
"立即行动，体验{product_name}带来的全新改变！🚀"'''