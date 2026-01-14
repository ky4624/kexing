import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Dict, List
from chat_agent import VideoScriptAgent

# 创建FastAPI应用
app = FastAPI(title="QAI Video Script Generator", version="3.0")

# 设置模板目录
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 连接管理器类
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agents: Dict[str, VideoScriptAgent] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        # 为每个客户端创建一个新的Agent实例
        self.agents[client_id] = VideoScriptAgent()
        # 发送欢迎消息
        welcome_msg = self.agents[client_id].start_conversation()
        if welcome_msg:
            await websocket.send_text(json.dumps({
                "type": "message",
                "content": welcome_msg,
                "sender": "assistant"
            }))

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.agents:
            del self.agents[client_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

# 主页路由
@app.get("/")
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 健康检查路由
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Server is running"}

# WebSocket 路由
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        # 将last_sent_index移到循环外部，确保在整个连接期间保持状态
        last_sent_index = -1
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "message":
                # 获取当前客户端的Agent实例
                agent = manager.agents[client_id]
                
                # 处理用户输入
                script_generated = agent.process_user_input(message["content"])
                
                # 获取对话历史长度
                history_length = len(agent.state["conversation_history"])
                
                # 只发送用户输入后新增的助手消息
                for i in range(last_sent_index + 1, history_length):
                    msg = agent.state["conversation_history"][i]
                    if msg["role"] == "assistant":
                        await websocket.send_text(json.dumps({
                            "type": "message",
                            "content": msg["content"],
                            "sender": "assistant"
                        }))
                
                # 更新已发送的消息索引
                last_sent_index = history_length - 1
                
                # 如果生成了脚本，询问是否需要新脚本
                if script_generated:
                    follow_up = "✨ 脚本已生成完成！您是否需要生成新的脚本？（是/否）"
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "content": follow_up,
                        "sender": "assistant"
                    }))
                    # 更新已发送的消息索引（包括这个后续问题）
                    last_sent_index += 1

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket 错误: {e}")
        import traceback
        traceback.print_exc()
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    # 使用0.0.0.0让服务器可以被外部访问
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")