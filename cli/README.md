# 🎬 Subtitle Translator CLI (GPU)

แปล Subtitle หนังญี่ปุ่น → ไทย ด้วย **faster-whisper** (GPU) + **Ollama** (local)
เร็วกว่าเวอร์ชัน browser **20-50 เท่า** สำหรับไฟล์ใหญ่

## เปรียบเทียบความเร็ว (ไฟล์ 1 ชั่วโมง)

| วิธี | Whisper | เวลา |
|---|---|---|
| Browser (transformers.js, CPU) | small | ~30-60 นาที |
| CLI นี้ (faster-whisper, **CPU**) | small | ~10-20 นาที |
| CLI นี้ (faster-whisper, **GPU**) | small | ~1-3 นาที |
| CLI นี้ (faster-whisper, **GPU**) | large-v3 | ~3-5 นาที |

---

## วิธีติดตั้ง (Windows)

### 1. ติดตั้ง Python 3.10+
ดาวน์โหลดจาก [python.org](https://www.python.org/downloads/) (อย่าลืม tick "Add Python to PATH")

### 2. ติดตั้ง dependencies

```powershell
cd cli
pip install -r requirements.txt
```

### 3. (เฉพาะ GPU) ตรวจสอบ CUDA

ต้องมี **NVIDIA GPU + CUDA 12.x driver** ติดตั้งแล้ว
เช็คด้วย: `nvidia-smi`

ถ้ารัน script แล้วเจอ error `cuDNN not found` หรือ `cublas not found`:

```powershell
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

หรือถ้าไม่มี GPU/ไม่อยากใช้:

```powershell
python translate.py movie.mp4 --device cpu --compute-type int8
```

### 4. ติดตั้ง Ollama + ดึง model

```powershell
# Download Ollama from https://ollama.com
$env:OLLAMA_ORIGINS="*"
ollama serve

# (อีก terminal)
ollama pull qwen2.5:7b
```

---

## วิธีใช้

### พื้นฐาน

```powershell
python translate.py "C:\path\to\movie.mp4"
```

ผลลัพธ์: `movie_th.srt` ที่โฟลเดอร์เดียวกัน

### Options

```powershell
# ใช้ Whisper ที่เร็วขึ้น (คุณภาพต่ำลงเล็กน้อย)
python translate.py movie.mp4 --whisper small

# ใช้ Ollama model อื่น
python translate.py movie.mp4 --ollama typhoon2

# ถอดเสียงอย่างเดียว ไม่แปล (ออกเป็น .srt ภาษาญี่ปุ่น)
python translate.py movie.mp4 --no-translate

# CPU only (ไม่ใช้ GPU)
python translate.py movie.mp4 --device cpu --compute-type int8

# กำหนดชื่อไฟล์ output
python translate.py movie.mp4 -o subs/translated.srt

# Beam size = 1 เพื่อความเร็ว (แม่นน้อยลง)
python translate.py movie.mp4 --beam-size 1
```

### ดูตัวเลือกทั้งหมด

```powershell
python translate.py --help
```

---

## Whisper Models

| Model | ขนาด | คุณภาพ | ความเร็ว (GPU) |
|---|---|---|---|
| `tiny` | 75 MB | ⭐⭐ | เร็วมาก |
| `base` | 145 MB | ⭐⭐⭐ | เร็ว |
| `small` | 480 MB | ⭐⭐⭐⭐ | กลาง |
| `medium` | 1.5 GB | ⭐⭐⭐⭐⭐ | ช้าหน่อย |
| `large-v3` | 3 GB | ⭐⭐⭐⭐⭐⭐ | ช้าสุด แต่แม่นที่สุด (**default**) |

แนะนำสำหรับหนังญี่ปุ่น: **`large-v3`** (คุณภาพดีที่สุด) หรือ **`medium`** (สมดุล)

---

## Workflow แนะนำสำหรับไฟล์ใหญ่

1. **ทดสอบก่อน** ด้วย `--whisper tiny --beam-size 1` เพื่อดูว่า workflow ทำงาน
   ```powershell
   python translate.py movie.mp4 --whisper tiny --beam-size 1
   ```
2. ถ้า preview ดูดี → รันจริงด้วย `large-v3`
   ```powershell
   python translate.py movie.mp4 --whisper large-v3
   ```

---

## Troubleshooting

### "cuDNN not found" หรือ "Failed to load cublas"
```powershell
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

### "CUDA out of memory"
- ปิด Ollama model อื่นก่อน: `ollama stop qwen2.5vl:7b`
- ใช้ Whisper ที่เล็กกว่า: `--whisper medium`
- ลด VRAM: `--compute-type int8_float16`

### Ollama แปลช้ามาก
- ตรวจสอบว่า GPU เหลือ VRAM พอ (อย่างน้อย 6GB สำหรับ qwen2.5:7b)
- ปิด model อื่นที่ค้างใน VRAM: `ollama ps` แล้ว `ollama stop <model>`

### "Ollama model not found"
```powershell
ollama pull qwen2.5:7b
```

### Whisper ถอดเสียงเป็นภาษาอื่น
Script บังคับ `language="ja"` แล้ว แต่ถ้ายังผิด ให้ตรวจสอบ:
- ไฟล์มีเสียงพูดจริงไหม
- เสียงดังพอไหม (ลอง normalize ด้วย VLC ก่อน)
