import edge_tts
import miniaudio

# Giọng đọc ruột của ông LPT
VOICE = "vi-VN-HoaiMyNeural" 

class EdgeTTSService:
    def __init__(self):
        pass

    async def get_tts_bytes(self, text: str) -> bytes:
        """Tải dữ liệu giọng nói từ Edge-TTS và giải mã sang PCM 16-bit, 16kHz, Mono cho ESP32"""
        if not text or not text.strip():
            return b""

        try:
            communicate = edge_tts.Communicate(text, VOICE)
            mp3_data = b""
            
            print(f"🔊 [EDGE TTS]: Đang kết nối và tải luồng MP3 từ Microsoft...",flush=True)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data += chunk["data"]

            if not mp3_data:
                print("⚠️ [TTS ERROR]: Không lấy được dữ liệu MP3 từ server.",flush=True)
                return b""
            
            print(f"🎛️ [EDGE TTS]: Đang giải mã MP3 sang PCM 16000Hz Mono...",flush=True)
            decoded = miniaudio.decode(
                mp3_data, 
                output_format=miniaudio.SampleFormat.SIGNED16, 
                nchannels=1, 
                sample_rate=16000
            )
            
            pcm_bytes = decoded.samples.tobytes()
            
            return pcm_bytes

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi trong quá trình xử lý TTS: {e}",flush=True)
            return b""