import edge_tts
import miniaudio

VOICE = "vi-VN-HoaiMyNeural"

class EdgeTTSService:
    def __init__(self):
        pass

    async def stream_tts_pcm(self, text: str, chunk_size: int = 2048):
        if not text or not text.strip():
            return

        try:
            communicate = edge_tts.Communicate(text, VOICE)
            mp3_bytes = bytearray()

            # 1. Tải toàn bộ dữ liệu MP3 từ Edge-TTS vào bộ nhớ
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_bytes.extend(chunk["data"])

            if not mp3_bytes:
                return

            # 2. Dùng miniaudio decode MP3 và resample về đúng 16000Hz, Mono (1 channel), 16-bit
            # miniaudio làm việc này bằng C nên tốc độ cực kỳ nhanh và mượt
            decoded = miniaudio.decode(
                mp3_bytes,
                output_format=miniaudio.SampleFormat.SIGNED16, # 16-bit PCM
                nchannels=1,                                    # Mono
                sample_rate=16000                              # Ép chuẩn về 16000Hz
            )

            pcm_data = decoded.samples.tobytes()

            # 3. Chia nhỏ PCM thành từng chunk và stream xuống WebSocket
            for i in range(0, len(pcm_data), chunk_size):
                yield pcm_data[i:i + chunk_size]

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi stream TTS với miniaudio: {e}", flush=True)