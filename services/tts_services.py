import edge_tts
import av

VOICE = "vi-VN-HoaiMyNeural"

class EdgeTTSService:
    def __init__(self):
        pass

    async def get_tts_bytes(self, text: str, chunk_size: int = 2048):
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

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    packets = codec.parse(chunk["data"])
                    for packet in packets:
                        frames = codec.decode(packet)
                        for frame in frames:
                            # Convert frame về 16000Hz trước khi lấy bytes
                            resampled_frames = resampler.resample(frame)
                            for r_frame in resampled_frames:
                                raw_pcm = r_frame.to_ndarray().tobytes()
                                pcm_buffer.extend(raw_pcm)

                                while len(pcm_buffer) >= chunk_size:
                                    yield bytes(pcm_buffer[:chunk_size])
                                    del pcm_buffer[:chunk_size]

            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi stream TTS: {e}", flush=True)