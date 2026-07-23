import os
import requests
import re

raw_key = os.environ.get("GROQ_API_KEY")
GROQ_API_KEY = f"Bearer {raw_key}" if raw_key else None
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """Bạn là Go Bi, một trợ lý AI thông minh, linh hoạt và đáng tin cậy.

### VAI TRÒ VÀ NĂNG LỰC CỐT LÕI:
- **Vai trò**: Trợ lý thông minh hỗ trợ tìm kiếm, tổng hợp và giải đáp thông tin một cách chính xác, nhanh chóng.
- **Tính cách**: Nhã nhặn, tự tin, nhạy bén và cực kỳ chu đáo trong cách truyền tải kiến thức.
- **Độ chính xác**: Cung cấp thông tin trung thực, đúng trọng tâm, dễ hiểu, không lan man hay đưa thông tin sai lệch.

### PHONG CÁCH GIAO TIẾP:
- **Giọng điệu**: Tự nhiên, văn minh, mang tính trợ lý hiện đại nhưng vẫn gần gũi, thân thiện.
- **Cách xưng hô**: Xưng Go Bi (hoặc tui/mình) và gọi người dùng là bạn (hoặc cậu/ông tùy ngữ cảnh trò chuyện) để tạo cảm giác tự nhiên.
- **Tránh tuyệt đối**: Cách nói chuyện quá máy móc, trả lời cộc lốc hoặc dùng các câu từ rập khuôn khô khan.

### BẮT BUỘC VỀ ĐỊNH DẠNG VÀ ĐỘ DÀI (PHỤC VỤ GIỌNG NÓI TTS):
1. **ĐỘ DÀI**: Câu trả lời ngắn gọn, cô đọng, giới hạn BẮT BUỘC tối đa dưới 300 từ.
2. **CẤM TỰ ĐỘNG ĐỊNH DẠNG**: Cấm dùng các ký tự Markdown (như **, *, #, _, `, ~).
3. **CẤM KÝ TỰ ĐẶC BIỆT & ICON**: Không dùng emoji, icon, dấu ngoặc kép (" "), ngoặc vuông hay ngoặc đơn.
"""

# 🧠 Kho chứa bộ nhớ nằm ẩn hoàn toàn trong service này
# Vì chạy local, tạm thời định danh mặc định cho thiết bị của ông LPT
GLOBAL_HISTORY = [
    {
        "role": "system", 
        "content": SYSTEM_PROMPT #"Bạn là Gobi, một người bạn thông minh, hài hước. Trả lời trên một đoạn văn duy nhất, không dùng các icon, emoji. Lời văn cực kỳ ngắn gọn, tự nhiên."
    }
]
MAX_HISTORY_LENGTH = 11  # Giữ lại khoảng 5 cặp hội thoại gần nhất để tránh tràn bộ nhớ

import re

def remove_emojis(text: str) -> str:
    """
    Hàm loại bỏ tất cả các emoji, icon Unicode ra khỏi chuỗi văn bản.
    """
    if not text:
        return ""
    
    clean = re.sub(r'[\*\_\#\`\~]', '', text)
    
    clean = re.sub(r'["“”‘’\'\(\)\[\]\{\}]', '', clean)

    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010FFFF"  # Các emoji chuẩn Unicode (bao gồm 🌟, 🎤, 🚀,...)
        "\u2600-\u26FF"          # Các biểu tượng Miscellaneous Symbols (☀️, ☔, ☕,...)
        "\u2700-\u27BF"          # Các biểu tượng Dingbats (✂️, ✈️, ✉️,...)
        "\u2300-\u23FF"          # Các biểu tượng kĩ thuật (⏰, ⏱️,...)
        "\u2B50"                 # Ký tự ngôi sao ⭐
        "\u200D"                 # Ký tự nối Zero Width Joiner trong emoji nhóm
        "]+", 
        flags=re.UNICODE
    )
    
    clean = emoji_pattern.sub('', clean)
    
    clean = re.sub(r'\s+', ' ', clean)
    
    return clean.strip()

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
        
        clean_ai_reply = remove_emojis(ai_reply)
        
        # 2. Lưu câu trả lời của AI vào lịch sử để làm vốn cho lần sau
        GLOBAL_HISTORY.append({"role": "assistant", "content": clean_ai_reply})
        
        # 3. Giới hạn độ dài lịch sử (cắt bớt câu cũ nhưng giữ lại System Prompt ở vị trí 0)
        if len(GLOBAL_HISTORY) > MAX_HISTORY_LENGTH:
            GLOBAL_HISTORY = [GLOBAL_HISTORY[0]] + GLOBAL_HISTORY[-(MAX_HISTORY_LENGTH-1):]
            
        return clean_ai_reply
        
    except Exception as e:
        print(f"[LỖI LLM SERVICE]: {e}")
        # Nếu lỗi thì xóa câu vừa hỏi ra khỏi lịch sử để tránh làm lệch mạch hội thoại
        if GLOBAL_HISTORY[-1]["role"] == "user":
            GLOBAL_HISTORY.pop()
        return "Não tui đang load chậm rồi ông LPT ơi, thử lại câu vừa rồi giúp tui nha!"