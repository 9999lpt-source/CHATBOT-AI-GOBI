import os
import re
import requests

raw_key = os.environ.get("GROQ_API_KEY")
GROQ_API_KEY = f"Bearer {raw_key}" if raw_key else None
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# 🧠 Kho chứa bộ nhớ nằm ẩn hoàn toàn trong service này
GLOBAL_HISTORY = [
    {
        "role": "system", 
        "content": (
            "Bạn là Gobi, một người bạn thông minh, hài hước. Bạn nói chuyện cực kỳ ngắn gọn, tự nhiên. "
            "Tuyệt đối không bao giờ trả lời quá cứng nhắc, không dùng các icon. "
            "CẤM xuất ra các thẻ <think></think> hoặc quá trình suy nghĩ, chỉ trả lời duy nhất câu thoại chính."
        )
    }
]
MAX_HISTORY_LENGTH = 11  # Giữ lại khoảng 5 cặp hội thoại gần nhất

def clean_reasoning_tags(text: str) -> str:
    """Xóa bỏ hoàn toàn khối <think>...</think> khỏi câu trả lời của LLM"""
    if not text:
        return ""
    # Xóa toàn bộ khối từ <think> đến </think> (bao gồm xuống dòng)
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text.strip()

def ask_groq_ai(user_text: str) -> str:
    global GLOBAL_HISTORY
    
    # 1. Tự động thêm câu hỏi mới của LPT vào kho lịch sử
    GLOBAL_HISTORY.append({"role": "user", "content": user_text})
    
    headers = {
        "Authorization": GROQ_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        # Tên model Qwen chuẩn trên Groq (hoặc dùng llama-3.3-70b-versatile)
        "model": "qwen-2.5-coder-32b", 
        "messages": GLOBAL_HISTORY
    }
    
    try:
        response = requests.post(GROQ_URL, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        
        raw_ai_reply = response_data["choices"][0]["message"]["content"]
        
        # 💡 LỌC BỎ KHỐI SUY NGHĨ: Chỉ lấy câu thoại cuối cùng
        ai_reply = clean_reasoning_tags(raw_ai_reply)
        
        # 2. Lưu câu trả lời ĐÃ LỌC SẠCH vào lịch sử để làm vốn cho lần sau
        GLOBAL_HISTORY.append({"role": "assistant", "content": ai_reply})
        
        # 3. Giới hạn độ dài lịch sử (giữ System Prompt ở vị trí 0)
        if len(GLOBAL_HISTORY) > MAX_HISTORY_LENGTH:
            GLOBAL_HISTORY = [GLOBAL_HISTORY[0]] + GLOBAL_HISTORY[-(MAX_HISTORY_LENGTH-1):]
            
        return ai_reply
        
    except Exception as e:
        print(f"[LỖI LLM SERVICE]: {e}")
        # Nếu lỗi thì xóa câu vừa hỏi ra khỏi lịch sử
        if GLOBAL_HISTORY and GLOBAL_HISTORY[-1]["role"] == "user":
            GLOBAL_HISTORY.pop()
        return "Não tui đang load chậm rồi ông LPT ơi, thử lại câu vừa rồi giúp tui nha!"