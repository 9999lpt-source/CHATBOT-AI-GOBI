import edge_tts
import av

# Giọng đọc Tiếng Việt chuẩn của Microsoft Edge
VOICE = "vi-VN-HoaiMyNeural"

class EdgeTTSService:
    def __init__(self):
        pass

    async def stream_tts_pcm(self, text: str, chunk_size: int = 2048):
        """
        Stream dữ liệu MP3 từ Edge-TTS, giải mã sang PCM (16kHz, Mono, 16-bit Little-Endian)
        và yield từng khối PCM (chunk_size = 2048 bytes) xuống ESP32 theo thời gian thực.
        """
        if not text or not text.strip():
            return

        try:
            communicate = edge_tts.Communicate(text, VOICE)
            codec = av.CodecContext.create('mp3', 'r')
            
            # Khởi tạo bộ Chuyển đổi Sample Rate về đúng 16000Hz, Mono, 16-bit
            resampler = av.AudioResampler(
                format='s16',       # 16-bit PCM
                layout='mono',      # 1 kênh Mono
                rate=16000          # Ép về 16000 Hz cho ESP32
            )
            
            pcm_buffer = bytearray()

            print("🔊 [EDGE TTS]: Đang stream và giải mã PCM chuẩn s16le...", flush=True)

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    packets = codec.parse(chunk["data"])
                    for packet in packets:
                        frames = codec.decode(packet)
                        for frame in frames:
                            # Convert frame về 16000Hz trước khi lấy bytes
                            resampled_frames = resampler.resample(frame)
                            for r_frame in resampled_frames:
                                # 💡 SỬA LỖI RÈ TIẾNG: Ép kiểu mảng NumPy về int16 Little-Endian ('<i2')
                                # Giúp ESP32 hiểu đúng thứ tự Byte, âm thanh sẽ cực kỳ trong rõ!
                                raw_pcm = r_frame.to_ndarray().astype('<i2').tobytes()
                                pcm_buffer.extend(raw_pcm)

                                while len(pcm_buffer) >= chunk_size:
                                    yield bytes(pcm_buffer[:chunk_size])
                                    del pcm_buffer[:chunk_size]

            # Gửi nấc dữ liệu PCM còn thừa ở cuối (nếu có)
            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi stream TTS: {e}", flush=True)