# 🎬 Subtitle Translator JP→TH

แปล Subtitle ภาษาญี่ปุ่น → ไทย โดยใช้ Ollama (Local AI)  
ไม่ต้องส่งข้อมูลออกอินเทอร์เน็ต ทุกอย่างรันบนเครื่องตัวเอง

## วิธีใช้

### 1. ติดตั้ง Ollama
ดาวน์โหลดที่ [ollama.com](https://ollama.com) แล้วติดตั้ง

### 2. ดึง Model ที่ต้องการ
```bash
ollama pull qwen2.5:7b
```

### 3. เปิด Ollama พร้อม CORS

**macOS / Linux:**
```bash
OLLAMA_ORIGINS=* ollama serve
```

**Windows (PowerShell):**
```powershell
$env:OLLAMA_ORIGINS="*"
ollama serve
```

หรือตั้ง Environment Variable ถาวร:  
`System Properties → Environment Variables → New → OLLAMA_ORIGINS = *`  
แล้วรีสตาร์ท Ollama

### 4. เปิดหน้าเว็บ

เปิดไฟล์ `index.html` ในเบราว์เซอร์  
หรือถ้า deploy บน GitHub Pages เปิด URL ที่ได้

### 5. ใช้งาน

1. กด **เลือกไฟล์ .srt** → เลือกไฟล์ subtitle ภาษาญี่ปุ่น
2. เลือก **Model** ที่ต้องการใช้
3. ดู **Preview** 10 บรรทัดแรกและ **ประมาณการเวลา**
4. กด **▶ เริ่มแปล**
5. รอ progress bar จนครบ 100%
6. กด **⬇ ดาวน์โหลด** เพื่อบันทึกไฟล์ `_th.srt`

---

## Models แนะนำ

| Model | คุณภาพ JP→TH | RAM | ความเร็ว |
|-------|-------------|-----|---------|
| `qwen2.5:7b` | ⭐⭐⭐⭐⭐ | ~8GB | เร็ว |
| `qwen2.5:14b` | ⭐⭐⭐⭐⭐ | ~16GB | ปานกลาง |
| `typhoon2` | ⭐⭐⭐⭐ | ~8GB | เร็ว |

---

## Deploy บน GitHub Pages

1. สร้าง repo ใหม่บน GitHub
2. Push ไฟล์ `index.html` และ `README.md`
3. ไปที่ **Settings → Pages → Branch: main → / (root)**
4. กด Save → ได้ URL: `https://username.github.io/repo-name`
