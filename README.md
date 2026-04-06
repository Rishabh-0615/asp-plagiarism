# ASP Plagiarism - AI Detection Service

Flask-based microservice for detecting AI-generated content in student submissions using the Desklib academic AI detection model.

## Architecture

```
Cloudinary (Student Submissions)
        ↓
  asp-plagiarism (Flask)
        ↓
  Hugging Face (Desklib Model)
        ↓
Spring Boot Backend / Supabase (Store Results)
        ↓
React Frontend (Display AI Score)
```

## Features

- ✅ AI-generated text detection
- ✅ Supports multiple file formats (PDF, DOCX, PPTX, TXT)
- ✅ Cloudinary integration for file downloads
- ✅ Supabase storage for results
- ✅ REST API endpoints
- ✅ Health check monitoring

## Setup

### 1. Clone/Navigate to Project

```bash
cd asp-plagiarism
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy example to .env
cp .env.example .env

# Edit .env and add your credentials:
# - HF_API_TOKEN (from https://huggingface.co/settings/tokens)
# - CLOUDINARY_* (from your Cloudinary account)
# - SUPABASE_* (from your Supabase project)
```

**Example .env:**
```
HF_API_TOKEN=your_huggingface_token_here
HF_MODEL_ID=desklib/ai-text-detector-academic-v1.01

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_TABLE=plagiarism_detections

FLASK_ENV=development
PORT=5000
```

### 5. Create Supabase Table

Run this SQL in your Supabase SQL editor:

```sql
CREATE TABLE plagiarism_detections (
    id BIGSERIAL PRIMARY KEY,
    submission_id TEXT NOT NULL UNIQUE,
    ai_score DECIMAL(5, 2) NOT NULL DEFAULT 0,
    human_score DECIMAL(5, 2) NOT NULL DEFAULT 0,
    confidence DECIMAL(3, 2) NOT NULL DEFAULT 0,
    label TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_submission_id ON plagiarism_detections(submission_id);
```

### 6. Run the Service

```bash
python app.py
```

Server starts at `http://localhost:5000`

## API Endpoints

### 1. Health Check
```
GET /api/v1/detect/health
```

### 2. Detect AI in Plain Text
```
POST /api/v1/detect/text
Content-Type: application/json

{
    "text": "Your submission text here",
    "submission_id": "sub_123",  // optional
    "save_to_db": true           // optional
}
```

**Response:**
```json
{
    "success": true,
    "ai_score": 85.50,
    "human_score": 14.50,
    "confidence": 0.95,
    "label": "AI-generated",
    "submission_id": "sub_123"
}
```

### 3. Detect AI from File URL
```
POST /api/v1/detect/file
Content-Type: application/json

{
    "file_url": "https://res.cloudinary.com/.../file.pdf",
    "submission_id": "sub_123",
    "save_to_db": true
}
```

### 4. Detect AI from Cloudinary
```
POST /api/v1/detect/cloudinary
Content-Type: application/json

{
    "public_id": "submissions/file123",
    "submission_id": "sub_123",
    "save_to_db": true
}
```

### 5. Get Detection Result
```
GET /api/v1/detect/result/sub_123
```

## Integration with Spring Boot Backend

### Example Controller Endpoint:

```java
@PostMapping("/api/v1/submissions/{id}/detect-ai")
public ResponseEntity<?> detectAI(@PathVariable String id) {
    // 1. Get submission file URL from Cloudinary
    String fileUrl = submissionService.getFileUrl(id);
    
    // 2. Call Flask service
    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.APPLICATION_JSON);
    
    String payload = String.format(
        "{\"file_url\":\"%s\",\"submission_id\":\"%s\",\"save_to_db\":true}",
        fileUrl, id
    );
    
    HttpEntity<String> request = new HttpEntity<>(payload, headers);
    RestTemplate template = new RestTemplate();
    
    ResponseEntity<Map> response = template.postForEntity(
        "http://localhost:5000/api/v1/detect/file",
        request,
        Map.class
    );
    
    // 3. Save result to your database
    Map<String, Object> result = response.getBody();
    submissionService.updateAIScore(id, 
        (Double) result.get("ai_score"),
        (String) result.get("label")
    );
    
    return ResponseEntity.ok(result);
}
```

## Response Score Interpretation

| AI Score Range | Human Score Range | Label | Action |
|---|---|---|---|
| 0-20% | 80-100% | Human-written | ✅ Accept |
| 21-50% | 50-79% | Mixed/Uncertain | ⚠️ Review |
| 51-100% | 0-49% | AI-generated | ❌ Flag |

## Model Information

**Desklib AI Detector v1.01**
- Developed by: Desklib
- Fine-tuned for: Academic writing (student submissions)
- Base Model: Microsoft DeBERTa v3-large
- Accuracy: ~95% on academic texts
- License: MIT

## Troubleshooting

### Error: "HuggingFace API error: 401"
- ✅ Solution: Check HF_API_TOKEN in .env file

### Error: "Could not extract text from file"
- ✅ Solution: Ensure file is in supported format (PDF, DOCX, PPTX, TXT)
- ✅ Check file is not corrupted

### Error: "Supabase not initialized"
- ✅ Solution: Verify SUPABASE_URL and SUPABASE_KEY in .env

### Error: "API request timeout"
- ✅ Solution: Increase timeout or reduce file size
- ✅ Check network connectivity

## Performance Notes

- Text limit: ~2000 characters (model limit)
- File download timeout: 30 seconds
- API response time: 3-10 seconds
- Best for: Text files, PDFs, DOCX, PPTX

## Security

- ✅ CORS enabled for frontend domains
- ✅ API token stored in environment variables
- ✅ Input validation on all endpoints
- ⚠️ Do not commit .env file with credentials

## Future Enhancements

- [ ] Batch processing for multiple submissions
- [ ] Caching for duplicate detection
- [ ] Advanced analytics dashboard
- [ ] Custom thresholds per institution
- [ ] Integration with LMS systems

## Support

For issues or questions:
1. Check logs: `tail -f app.log`
2. Verify API keys in .env
3. Test endpoints with Postman

---

**Version:** 1.0.0  
**Last Updated:** January 2024  
**Model:** Desklib AI Text Detector v1.01
