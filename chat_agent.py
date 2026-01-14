import json
import re
from typing import Dict, List, Optional
from config import Config
from utils import get_qwen_response, parse_json_response

class VideoScriptAgent:
    def __init__(self):
        self.config = Config()
        self.state = {
            "collected": {
                "product": None,
                "audience": None,
                "tone": None,
                "style": None,
                "language": None,
                "duration": None,
                "core_function": None
            },
            "missing_fields": ["product", "audience", "tone", "style", "language", "duration"],
            "last_action": None,
            "conversation_history": []
        }
        self.questions = [
            "我们在推广什么？可以是产品、服务、品牌、活动、APP、课程等任意内容 👉 请直接告诉我推广对象。",
            "目标受众是谁？可以是任何人群类型 👉 请描述主要受众人群。",
            "期望的视频情绪或基调是什么？可以是任何情绪或基调 👉 请告诉我你希望观众看完后的感觉。",
            "偏好的视频风格是？可以是任何风格 👉 可以选择一种或组合多种风格。",
            "视频语言是什么？可以是任何语言 👉 请告诉我你希望视频里的台词 / 字幕使用哪种语言。",
            "视频时长选择：10 秒（默认，节奏更快）或 15 秒（信息更丰富，更有情绪铺垫）👉 请回复 10秒 或 15秒。"
        ]
    
    def start_conversation(self):
        """开始对话"""
        # 检查是否已经有欢迎消息，避免重复添加
        if not self.state["conversation_history"]:
            welcome_msg = "欢迎使用 QAI 视频脚本生成器 3.0！🎬我将通过 6 个简单问题，为您量身打造一个专业、可直接用于视频生成的脚本。让我们一步一步来吧 😊\n\n问题 1 / 6\n" + self.questions[0]
            self.state["conversation_history"].append({"role": "assistant", "content": welcome_msg})
            return welcome_msg
        return None
    
    def process_user_input(self, user_input: str):
        """处理用户输入"""
        # 检查是否是对"是否需要生成新脚本"的回答
        if self.state["conversation_history"] and "您是否需要生成新的脚本？" in self.state["conversation_history"][-1]["content"]:
            if user_input.strip() in ["是", "是的", "好的", "需要"]:
                # 重置对话状态
                self.state = {
                    "collected": {
                        "product": None,
                        "audience": None,
                        "tone": None,
                        "style": None,
                        "language": None,
                        "duration": None,
                        "core_function": None
                    },
                    "missing_fields": ["product", "audience", "tone", "style", "language", "duration"],
                    "last_action": None,
                    "conversation_history": self.state["conversation_history"].copy()
                }
                # 开始新的对话
                welcome_msg = "好的！让我们开始生成新的脚本吧 😊\n\n问题 1 / 6\n" + self.questions[0]
                self.state["conversation_history"].append({"role": "assistant", "content": welcome_msg})
                return False
            elif user_input.strip() in ["否", "不是", "不需要"]:
                # 结束对话
                end_msg = "感谢使用 QAI 视频脚本生成器！如果您有任何其他需求，随时欢迎回来 😊"
                self.state["conversation_history"].append({"role": "assistant", "content": end_msg})
                return False
        
        self.state["conversation_history"].append({"role": "user", "content": user_input})
        
        # 检查是否正在询问core_function，如果是则直接保存
        if "core_function" in self.state["missing_fields"]:
            self.state["collected"]["core_function"] = user_input
            self.state["missing_fields"].remove("core_function")
            
            # 继续提问或生成脚本
            if self._all_fields_collected():
                return self._generate_script()
            else:
                self._ask_next_question()
                return False
        
        # 先进行意图识别
        intent = self._recognize_intent(user_input)
        
        if intent["type"] == "B":
            # 修改已有字段
            field = intent["field"]
            new_value = intent["value"]
            self.state["collected"][field] = new_value
            
            # 如果修改了product，重新评估是否需要core_function
            if field == "product":
                self._check_core_function_need()
            
            response = f"✅ 已更新 {field} 为：{new_value}"
            self.state["conversation_history"].append({"role": "assistant", "content": response})
            return False
        
        elif intent["type"] == "A":
            # 提供新字段值
            extracted = self._extract_fields(user_input)
            for field, value in extracted.items():
                if value and self.state["collected"][field] is None:
                    self.state["collected"][field] = value
                    if field in self.state["missing_fields"]:
                        self.state["missing_fields"].remove(field)
            
            # 检查是否需要core_function
            if "product" in extracted and extracted["product"]:
                self._check_core_function_need()
        
        elif intent["type"] == "D":
            # 请求生成脚本
            if self._all_fields_collected():
                return self._generate_script()
            else:
                response = f"📋 我们还需要以下信息：{', '.join(self.state['missing_fields'])}"
                self.state["conversation_history"].append({"role": "assistant", "content": response})
                return False
        
        elif intent["type"] == "C" or intent["type"] == "E":
            # 跳过或其他闲聊
            response = "😊 好的，让我们继续完成脚本生成。"
            self.state["conversation_history"].append({"role": "assistant", "content": response})
        
        # 继续提问或生成脚本
        if self._all_fields_collected():
            return self._generate_script()
        else:
            self._ask_next_question()
            return False

    def _recognize_intent(self, user_input: str) -> Dict:
        """识别用户意图"""
        prompt = f"""
        用户输入：{user_input}
        
        请先判断意图类型（单选）：
        A. 提供新字段值
        B. 修改已有字段
        C. 跳过/不想回答
        D. 请求生成脚本
        E. 其他闲聊
        
        如果是 B，请指出修改哪个字段，并提取新值。
        
        回答格式（严格JSON）：
        {{"type": "A/B/C/D/E", "field": "字段名（如果是B）", "value": "新值（如果是B）"}}
        """
        
        response = get_qwen_response(prompt)
        try:
            return parse_json_response(response)
        except Exception:
            # 如果解析失败，默认按提供新字段值处理
            return {"type": "A"}
    
    def _extract_fields(self, user_input: str) -> Dict[str, Optional[str]]:
        """从用户输入中提取字段值"""
        # 首先尝试通过AI提取
        prompt = f"""
        用户输入：{user_input}
        
        请从用户输入中提取以下字段的值（如果有）：
        - product（推广对象）
        - audience（目标受众）
        - tone（情绪基调）
        - style（视频风格）
        - language（语言）
        - duration（10秒 / 15秒）
        
        回答格式（严格JSON）：
        {{"product": "值或null", "audience": "值或null", "tone": "值或null", "style": "值或null", "language": "值或null", "duration": "值或null"}}
        """
        
        response = get_qwen_response(prompt)
        try:
            extracted = parse_json_response(response)
        except Exception:
            extracted = {}
        
        # 如果AI提取成功，直接返回结果
        if any(extracted.values()):
            return extracted
        
        # 改进的回退逻辑：根据当前的缺失字段来判断用户正在回答的问题
        user_input = user_input.strip()
        if not user_input:
            return extracted
        
        # 查看当前缺失的第一个字段
        if self.state["missing_fields"]:
            current_field = self.state["missing_fields"][0]
            extracted[current_field] = user_input
        
        return extracted
    
    def _check_core_function_need(self):
        """检查是否需要core_function"""
        product = self.state["collected"]["product"]
        if not product:
            return
        
        prompt = f"""
        【子任务】请判断以下 product 描述是否已包含明确的核心功能（即说明了"为谁解决什么问题"）：
        >> "{product}"
        
        回答格式（严格JSON）：
        {{"needs_core_function": true/false, "reason": "..."}}
        """
        
        response = get_qwen_response(prompt)
        try:
            result = parse_json_response(response)
            if result["needs_core_function"]:
                if "core_function" not in self.state["missing_fields"]:
                    self.state["missing_fields"].append("core_function")
            else:
                if "core_function" in self.state["missing_fields"]:
                    self.state["missing_fields"].remove("core_function")
                self.state["collected"]["core_function"] = f"{product}的核心功能"
        except Exception:
            # 默认需要core_function
            if "core_function" not in self.state["missing_fields"]:
                self.state["missing_fields"].append("core_function")
    
    def _all_fields_collected(self) -> bool:
        """检查是否所有字段都已收集"""
        return len(self.state["missing_fields"]) == 0

    def _ask_next_question(self):
        """问下一个问题"""
        # 优先检查core_function
        if "core_function" in self.state["missing_fields"]:
            question = f"🔍 关键补充：这个【{self.state['collected']['product']}】主要是做什么的？"
            self.state["conversation_history"].append({"role": "assistant", "content": question})
            return
        
        # 按顺序问其他问题
        field_order = ["product", "audience", "tone", "style", "language", "duration"]
        for i, field in enumerate(field_order):
            if field in self.state["missing_fields"]:
                question = f"问题 {i+1} / 6\n{self.questions[i]}"
                self.state["conversation_history"].append({"role": "assistant", "content": question})
                return
    
    def _generate_script(self):
        """生成视频脚本"""
        # 确认关键信息
        collected_info = "\n".join([f"✅ {k}: {v}" for k, v in self.state["collected"].items() if v])
        confirmation = f"📋 确认关键信息：\n{collected_info}\n\n正在生成脚本..."
        self.state["conversation_history"].append({"role": "assistant", "content": confirmation})
        
        # 生成脚本
        prompt = f"""
        你是一位顶级短视频文案专家。请基于以下需求，生成一个【{self.state['collected']['duration']}】{self.state['collected']['language']}视频脚本：
        推广对象：{self.state['collected']['product']}
        目标受众：{self.state['collected']['audience']}
        核心功能：{self.state['collected']['core_function']}
        情绪基调：{self.state['collected']['tone']}
        视频风格：{self.state['collected']['style']}
        语言：{self.state['collected']['language']}
        
        要求：
        1. 分{4 if self.state['collected']['duration'] == '10秒' else 5}段，每段标注时间（如 [0-3s]）
        2. 情绪递进：引发好奇 → 放大痛点 → 亮出方案 → 建立信任 → 强CTA
        3. 每段包含：【视觉画面描述】+ 【台词/旁白】
        4. 符合短视频平台算法（前3秒必须抓住注意力）
        5. 语言口语化，避免专业术语
        6. 结尾必须有明确的行动号召（CTA）
        """
        
        script = get_qwen_response(prompt)
        self.state["conversation_history"].append({"role": "assistant", "content": script})
        return True