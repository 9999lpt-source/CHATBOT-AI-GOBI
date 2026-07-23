import edge_tts
import av

VOICE = "vi-VN-HoaiMyNeural"

class EdgeTTSService:
    def __init__(self):
        pass

    async def stream_tts_pcm(self, text: str, chunk_size: int = 2048):
        if not text or not text.strip():
            return

        try:
            communicate = edge_tts.Communicate(text, VOICE)
            codec = av.CodecContext.create('mp3', 'r')
            
            pcm_buffer = bytearray()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    packets = codec.parse(chunk["data"])
                    for packet in packets:
                        frames = codec.decode(packet)
                        for frame in frames:
                            # Lấy trực tiếp raw bytes từ frame gốc (không qua resampler)
                            raw_pcm = frame.to_ndarray().tobytes()
                            pcm_buffer.extend(raw_pcm)

                            while len(pcm_buffer) >= chunk_size:
                                yield bytes(pcm_buffer[:chunk_size])
                                del pcm_buffer[:chunk_size]

            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi stream TTS: {e}", flush=True)