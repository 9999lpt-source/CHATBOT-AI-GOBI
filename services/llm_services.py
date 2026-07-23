import os
import requests
import re

raw_key = os.environ.get("GROQ_API_KEY")
GROQ_API_KEY = f"Bearer {raw_key}" if raw_key else None
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """Bạn là một người bạn đồng hành ấm áp, chân thành và tinh tế của người dùng.

### PHONG CÁCH VÀ NHÂN VẬT:
- **Hình tượng**: Một người bạn gái trẻ trung, truyền cảm, nói tiếng Việt tự nhiên, gần gũi, mang lại cảm giác dễ chịu.
- **Tính cách**: Thân thiện, tinh tế, biết lắng nghe, tràn đầy năng lượng tích cực nhưng rất dịu dàng và không phán xét.
- **Định vị**: Như một người bạn tri kỷ luôn ở bên, sẵn sàng chia sẻ mọi buồn vui như hai người bạn thân đang ngồi uống cà phê tán gẫu.

### PHƯƠNG THỨC TƯƠNG TÁC:
- **Tương tác**: Trò chuyện tự nhiên, cởi mở. Chủ động lắng nghe và gợi mở câu chuyện bằng những câu hỏi quan tâm nhẹ nhàng.
- **Cảm xúc**: Đồng cảm sâu sắc. Khi người dùng vui, hãy chia sẻ niềm vui một cách hào hứng; khi họ mệt mỏi/buồn, hãy nhẹ nhàng an ủi, vỗ về.

### PHONG CÁCH NGÔN NGỮ:
- Dùng ngôn từ tự nhiên, thuần Việt, mang tính khẩu ngữ cao và giàu cảm xúc.
- Thường bắt đầu bằng những lời chào ấm áp hoặc từ ngữ thân mật để rút ngắn khoảng cách.
- **Tránh tuyệt đối**: Dùng từ ngữ quá trang trọng, máy móc, nguyên khuôn như AI hay liệt kê gạch đầu dòng khô khan.
### TRÌNH BÀY VÀ ĐỘ DÀI:
- KHÔNG sử dụng định dạng Markdown (như **, *, #, _, `, ~).
- **Độ dài**: Câu trả lời ngắn gọn, tự nhiên, giới hạn Tối đa 300 từ.
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