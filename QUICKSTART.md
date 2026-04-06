# 🚀 Quick Start Guide - ASP Plagiarism AI Detection

## ⚡ 5-Minute Setup

### Step 1: Navigate to Project
```bash
cd asp-plagiarism
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Credentials
The `.env` file is already created with your HF token. Update Cloudinary and Supabase:

```bash
# Edit .env file
nano .env
# or open with any text editor
```

**Required in .env:**
```
CLOUDINARY_CLOUD_NAME=your_value
CLOUDINARY_API_KEY=your_value
CLOUDINARY_API_SECRET=your_value

SUPABASE_URL=your_value
SUPABASE_KEY=your_value
```

### Step 5: Create Supabase Table
Run in Supabase SQL Editor:
```sql
CREATE TABLE plagiarism_detections (
    id BIGSERIAL PRIMARY KEY,
    submission_id TEXT NOT NULL UNIQUE,
    ai_score DECIMAL(5, 2) NOT NULL DEFAULT 0,
    human_score DECIMAL(5, 2) NOT NULL DEFAULT 0,
    confidence DECIMAL(3, 2) NOT NULL DEFAULT 0,
    label TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed'
);
```

### Step 6: Start the Service
```bash
# Windows
run.bat

# macOS/Linux
chmod +x run.sh
./run.sh

# Or directly
python app.py
```

✅ Service running at: `http://localhost:5000`

---

## 📋 Project Structure

```
asp-plagiarism/
├── app.py                    # Main Flask application
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (YOUR KEYS HERE)
├── .env.example              # Environment template
├── .gitignore               # Git ignore rules
│
├── services/                # Business logic
│   ├── huggingface_service.py    # HF model integration
│   ├── cloudinary_service.py     # Cloudinary download
│   ├── supabase_service.py       # Supabase storage
│   └── text_extraction.py        # File text extraction
│
├── routes/                  # API endpoints
│   └── detect_routes.py     # AI detection endpoints
│
├── models/                  # Data models
│   └── response_models.py   # Response schemas
│
├── README.md                # Full documentation
├── INTEGRATION_GUIDE.md     # Spring Boot integration
├── QUICKSTART.md            # This file
├── run.bat                  # Windows startup script
└── run.sh                   # Linux/macOS startup script
```

---

## 🔌 API Endpoints

### Health Check
```bash
curl http://localhost:5000/api/v1/detect/health
```

### Detect AI in Text
```bash
curl -X POST http://localhost:5000/api/v1/detect/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your submission text here",
    "submission_id": "sub_123",
    "save_to_db": true
}'
```

### Detect AI from File
```bash
curl -X POST http://localhost:5000/api/v1/detect/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "https://res.cloudinary.com/.../file.pdf",
    "submission_id": "sub_123",
    "save_to_db": true
}'
```

### Get Saved Result
```bash
curl http://localhost:5000/api/v1/detect/result/sub_123
```

---

## 📊 Response Example

```json
{
    "success": true,
    "submission_id": "sub_123",
    "ai_score": 85.50,
    "human_score": 14.50,
    "confidence": 0.95,
    "label": "AI-generated"
}
```

## 🎯 Score Interpretation

| AI Score | Status | Action |
|----------|--------|--------|
| 0-20% | Human-written | ✅ Accept |
| 21-50% | Mixed/Uncertain | ⚠️ Review |
| 51-100% | AI-generated | ❌ Flag |

---

## 🔗 Connect to Spring Boot

### Pre-requisites
- Spring Boot running on `localhost:8080`
- Add the integration code from `INTEGRATION_GUIDE.md`

### Example Call
```bash
curl -X POST http://localhost:8080/api/v1/submissions/1/analyze-ai
```

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `401 Unauthorized` | Check HF_API_TOKEN in `.env` |
| `Connection refused` | Ensure Flask is running |
| `No module named 'flask'` | Activate venv: `venv\Scripts\activate` (Windows) |
| Empty responses | Check text/file is not empty |

---

## 📁 File Upload Flow

```
Student File (PDF/DOCX)
    ↓
Cloudinary (stored)
    ↓
Flask receives URL
    ↓
Extract text (PyPDF2/python-docx)
    ↓
Send to HF Desklib Model
    ↓
Get AI % score
    ↓
Save to Supabase
    ↓
Return to Spring Boot
    ↓
Display in React UI
```

---

## 🧪 Test the Service

### 1. Start Flask
```bash
python app.py
```

### 2. In another terminal, test endpoint
```bash
curl http://localhost:5000/api/v1/detect/health
```

Expected response:
```json
{
    "status": "operational",
    "service": "asp-plagiarism (AI Detection)",
    "model": "desklib/ai-text-detector-academic-v1.01"
}
```

### 3. Test with sample text
```bash
curl -X POST http://localhost:5000/api/v1/detect/text \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a student submission text.", "submission_id": "test123"}'
```

---

## 📦 Model Details

- **Model**: desklib/ai-text-detector-academic-v1.01
- **Provider**: Hugging Face
- **Accuracy**: ~95% on academic texts
- **Input**: Text (up to 2000 chars)
- **Output**: AI score, Human score, Confidence
- **License**: MIT

---

## 🔐 Security Notes

✅ API token stored in `.env` (not committed)  
✅ CORS enabled for frontend  
✅ Input validation on all endpoints  
✅ No credentials in logs  

⚠️ Don't share `.env` file!

---

## 📞 Support

1. **Check Logs**: `tail -f app.log`
2. **Verify Config**: Review `.env` file
3. **Check Services**: 
   - HuggingFace API: `huggingface.co`
   - Cloudinary: `cloudinary.com`
   - Supabase: `supabase.com`

---

**Ready?** Run `python app.py` and start detecting AI! 🚀
