import os
import requests

raw_key = os.environ.get("GROQ_API_KEY")
GROQ_API_KEY = f"Bearer {raw_key}" if raw_key else None
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# 🧠 Kho chứa bộ nhớ nằm ẩn hoàn toàn trong service này
# Vì chạy local, tạm thời định danh mặc định cho thiết bị của ông LPT
G# 🧠 Kho chứa bộ nhớ với System Prompt tối ưu riêng cho gpt-oss-120b
GLOBAL_HISTORY = [
    {
        "role": "system", 
        "content": (
            "Bạn tên là Gobi, một trợ lý AI thông minh, cực kỳ vui vẻ và hài hước một cách rất tự nhiên. "
            "Quy tắc phát ngôn bắt buộc: "
            "1. BẮT BUỘC trả lời liền mạch trong DUY NHẤT MỘT ĐOẠN VĂN, tuyệt đối KHÔNG được xuống dòng, không dùng dấu gạch đầu dòng hay danh sách. "
            "2. KHÔNG dùng bất kỳ icon, emoji hay ký tự đặc biệt nào. "
            "3. TRUNG THỰC TUYỆT ĐỐI: Chỉ trả lời dựa trên sự thật và kiến thức chuẩn xác, cấm tự bịa đặt thông tin, cấm chém gió sai sự thật. "
            "4. Giữ câu văn ngắn gọn, dí dỏm, nói chuyện tự nhiên như một người bạn thân thiết."
        )
    }
]
MAX_HISTORY_LENGTH = 11  # Giữ lại khoảng 5 cặp hội thoại gần nhất để tránh tràn bộ nhớ

def ask_groq_ai(user_text: str) -> str:
    global GLOBAL_HISTORY
    
    # 1. Tự động thêm câu hỏi mới của ông LPT vào kho lịch sử ngầm
    GLOBAL_HISTORY.append({"role": "user", "content": user_text})
    
    headers = {
        "Authorization": GROQ_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-oss-120b", #llama-3.3-70b-versatile
        "messages": GLOBAL_HISTORY  # 🚀 Gửi kèm toàn bộ lịch sử đã tích lũy lên Groq
    }
    
    try:
        response = requests.post(GROQ_URL, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        
        ai_reply = response_data["choices"][0]["message"]["content"]
        
        # 2. Lưu câu trả lời của AI vào lịch sử để làm vốn cho lần sau
        GLOBAL_HISTORY.append({"role": "assistant", "content": ai_reply})
        
        # 3. Giới hạn độ dài lịch sử (cắt bớt câu cũ nhưng giữ lại System Prompt ở vị trí 0)
        if len(GLOBAL_HISTORY) > MAX_HISTORY_LENGTH:
            GLOBAL_HISTORY = [GLOBAL_HISTORY[0]] + GLOBAL_HISTORY[-(MAX_HISTORY_LENGTH-1):]
            
        return ai_reply
        
    except Exception as e:
        print(f"[LỖI LLM SERVICE]: {e}")
        # Nếu lỗi thì xóa câu vừa hỏi ra khỏi lịch sử để tránh làm lệch mạch hội thoại
        if GLOBAL_HISTORY[-1]["role"] == "user":
            GLOBAL_HISTORY.pop()
        return "Não tui đang load chậm rồi ông LPT ơi, thử lại câu vừa rồi giúp tui nha!"