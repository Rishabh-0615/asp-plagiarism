# Integration Guide: ASP Plagiarism Service with Spring Boot

## Overview

This guide explains how to integrate the Flask AI Detection service with your Spring Boot backend.

## Architecture Flow

```
1. Student submits assignment → Stored in Cloudinary
2. Faculty reviews submission → Spring Boot fetches file URL
3. Spring Boot calls Flask service → Flask downloads & analyzes
4. Flask returns AI score → Spring Boot saves to database
5. Frontend displays result → Shows AI detection percentage
```

## Step 1: Add HttpClient to Spring Boot

### Add Dependency (pom.xml)

Already in your project, but ensure you have:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- For REST calls -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
```

## Step 2: Create Flask Service Integration Class

### File: `src/main/java/com/assignmentportal/service/AIDetectionService.java`

```java
package com.assignmentportal.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
public class AIDetectionService {

    @Value("${flask.service.url:http://localhost:5000}")
    private String flaskServiceUrl;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public AIDetectionService() {
        this.restTemplate = new RestTemplate();
        this.objectMapper = new ObjectMapper();
    }

    /**
     * Detect AI-generated content from file URL
     * 
     * @param fileUrl Cloudinary file URL
     * @param submissionId Unique submission identifier
     * @return AI Detection result
     */
    public AIDetectionResult detectFromFile(String fileUrl, String submissionId) {
        try {
            // Prepare request payload
            Map<String, Object> payload = new HashMap<>();
            payload.put("file_url", fileUrl);
            payload.put("submission_id", submissionId);
            payload.put("save_to_db", true);

            // Set headers
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // Create request
            HttpEntity<Map> request = new HttpEntity<>(payload, headers);

            // Call Flask service
            String endpoint = flaskServiceUrl + "/api/v1/detect/file";
            Map response = restTemplate.postForObject(endpoint, request, Map.class);

            log.info("AI Detection result for {}: {}", submissionId, response);

            // Parse response
            return parseDetectionResult(response);

        } catch (Exception e) {
            log.error("Error calling AI detection service: {}", e.getMessage(), e);
            return AIDetectionResult.error(e.getMessage());
        }
    }

    /**
     * Detect AI-generated content from plain text
     * 
     * @param text Submission text
     * @param submissionId Unique submission identifier
     * @return AI Detection result
     */
    public AIDetectionResult detectFromText(String text, String submissionId) {
        try {
            // Prepare request payload
            Map<String, Object> payload = new HashMap<>();
            payload.put("text", text);
            payload.put("submission_id", submissionId);
            payload.put("save_to_db", true);

            // Set headers
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // Create request
            HttpEntity<Map> request = new HttpEntity<>(payload, headers);

            // Call Flask service
            String endpoint = flaskServiceUrl + "/api/v1/detect/text";
            Map response = restTemplate.postForObject(endpoint, request, Map.class);

            log.info("AI Detection result for {}: {}", submissionId, response);

            // Parse response
            return parseDetectionResult(response);

        } catch (Exception e) {
            log.error("Error calling AI detection service: {}", e.getMessage(), e);
            return AIDetectionResult.error(e.getMessage());
        }
    }

    /**
     * Get saved AI detection result
     * 
     * @param submissionId Unique submission identifier
     * @return Stored AI Detection result
     */
    public AIDetectionResult getDetectionResult(String submissionId) {
        try {
            String endpoint = flaskServiceUrl + "/api/v1/detect/result/" + submissionId;
            Map response = restTemplate.getForObject(endpoint, Map.class);

            log.info("Retrieved AI Detection result for {}: {}", submissionId, response);

            return parseDetectionResult(response);

        } catch (Exception e) {
            log.error("Error retrieving AI detection result: {}", e.getMessage(), e);
            return AIDetectionResult.error(e.getMessage());
        }
    }

    /**
     * Check Flask service health
     */
    public boolean isServiceHealthy() {
        try {
            String endpoint = flaskServiceUrl + "/api/v1/detect/health";
            Map response = restTemplate.getForObject(endpoint, Map.class);
            return response != null && "operational".equals(response.get("status"));
        } catch (Exception e) {
            log.error("Flask service health check failed: {}", e.getMessage());
            return false;
        }
    }

    // Helper method to parse Flask response
    private AIDetectionResult parseDetectionResult(Map response) {
        if (response == null) {
            return AIDetectionResult.error("No response from Flask service");
        }

        AIDetectionResult result = new AIDetectionResult();
        result.setSuccess((Boolean) response.getOrDefault("success", false));
        result.setAiScore(((Number) response.getOrDefault("ai_score", 0)).doubleValue());
        result.setHumanScore(((Number) response.getOrDefault("human_score", 0)).doubleValue());
        result.setConfidence(((Number) response.getOrDefault("confidence", 0)).doubleValue());
        result.setLabel((String) response.getOrDefault("label", "Unknown"));
        result.setSubmissionId((String) response.get("submission_id"));

        return result;
    }
}
```

## Step 3: Create AIDetectionResult Data Class

### File: `src/main/java/com/assignmentportal/dto/AIDetectionResult.java`

```java
package com.assignmentportal.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AIDetectionResult {
    private Boolean success;
    private Double aiScore;
    private Double humanScore;
    private Double confidence;
    private String label;
    private String submissionId;
    private String error;

    public static AIDetectionResult error(String message) {
        AIDetectionResult result = new AIDetectionResult();
        result.setSuccess(false);
        result.setError(message);
        result.setAiScore(0.0);
        result.setHumanScore(0.0);
        result.setConfidence(0.0);
        return result;
    }
}
```

## Step 4: Add Configuration

### File: `application.properties` or `application.yml`

```properties
# AI Detection Service
flask.service.url=http://localhost:5000

# Logging
logging.level.com.assignmentportal.service.AIDetectionService=INFO
```

## Step 5: Use in Controller/Service

### Example Controller:

```java
@RestController
@RequestMapping("/api/v1/submissions")
@Slf4j
public class SubmissionController {

    @Autowired
    private AIDetectionService aiDetectionService;

    @Autowired
    private SubmissionService submissionService;

    /**
     * Analyze submission for AI content
     */
    @PostMapping("/{submissionId}/analyze-ai")
    public ResponseEntity<?> analyzeAI(@PathVariable Long submissionId) {
        try {
            // Get submission from database
            Submission submission = submissionService.findById(submissionId);
            if (submission == null) {
                return ResponseEntity.notFound().build();
            }

            // Get file URL from Cloudinary
            String fileUrl = submission.getFileUrl(); // or get from Cloudinary

            // Call AI Detection service
            AIDetectionResult result = aiDetectionService.detectFromFile(
                fileUrl,
                submissionId.toString()
            );

            if (!result.getSuccess()) {
                log.error("AI Detection failed: {}", result.getError());
                return ResponseEntity.status(500).body(result);
            }

            // Save result to your database
            submission.setAiScore(result.getAiScore());
            submission.setAiLabel(result.getLabel());
            submission.setAiConfidence(result.getConfidence());
            submissionService.save(submission);

            // Return result
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            log.error("Error analyzing submission: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(
                Map.of("error", e.getMessage())
            );
        }
    }

    /**
     * Get AI detection result for submission
     */
    @GetMapping("/{submissionId}/ai-result")
    public ResponseEntity<?> getAIResult(@PathVariable Long submissionId) {
        AIDetectionResult result = aiDetectionService.getDetectionResult(
            submissionId.toString()
        );
        return ResponseEntity.ok(result);
    }
}
```

## Step 6: Add to Submission Entity

### File: `src/main/java/com/assignmentportal/entity/Submission.java`

```java
@Entity
@Table(name = "submissions")
@Data
public class Submission {
    // ... existing fields ...

    @Column(name = "ai_score")
    private Double aiScore;

    @Column(name = "ai_label")
    private String aiLabel; // "AI-generated" or "Human-written"

    @Column(name = "ai_confidence")
    private Double aiConfidence;

    @Column(name = "ai_analyzed_at")
    private LocalDateTime aiAnalyzedAt;

    @Column(name = "ai_analysis_status")
    private String aiAnalysisStatus; // "pending", "completed", "failed"
}
```

## Step 7: Database Migration (Flyway/Liquibase)

### SQL Migration:

```sql
ALTER TABLE submissions ADD COLUMN ai_score DECIMAL(5, 2);
ALTER TABLE submissions ADD COLUMN ai_label VARCHAR(50);
ALTER TABLE submissions ADD COLUMN ai_confidence DECIMAL(3, 2);
ALTER TABLE submissions ADD COLUMN ai_analyzed_at TIMESTAMP;
ALTER TABLE submissions ADD COLUMN ai_analysis_status VARCHAR(20) DEFAULT 'pending';

CREATE INDEX idx_ai_score ON submissions(ai_score);
```

## Step 8: Frontend Integration

### React Component Example:

```jsx
// SubmissionAnalysis.jsx
import { useState, useEffect } from 'react';

function SubmissionAnalysis({ submissionId }) {
  const [aiResult, setAiResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeAI = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/submissions/${submissionId}/analyze-ai`,
        { method: 'POST' }
      );
      const data = await response.json();
      setAiResult(data);
    } catch (error) {
      console.error('Error analyzing:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-analysis">
      <button onClick={analyzeAI} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze for AI'}
      </button>

      {aiResult && (
        <div className="result">
          <h3>AI Detection Result</h3>
          <p>AI Score: <strong>{aiResult.aiScore}%</strong></p>
          <p>Label: <strong>{aiResult.label}</strong></p>
          <p>Confidence: {(aiResult.confidence * 100).toFixed(1)}%</p>

          <div className="score-bar">
            <div 
              className="ai-portion" 
              style={{ width: `${aiResult.aiScore}%` }}
            >
              AI: {aiResult.aiScore}%
            </div>
            <div 
              className="human-portion" 
              style={{ width: `${aiResult.humanScore}%` }}
            >
              Human: {aiResult.humanScore}%
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SubmissionAnalysis;
```

## Configuration Checklist

- [ ] Flask service running on `localhost:5000`
- [ ] HuggingFace API token configured
- [ ] Cloudinary credentials set
- [ ] Supabase database table created
- [ ] Spring Boot `flask.service.url` configured
- [ ] Submission entity updated with AI columns
- [ ] Database migration applied
- [ ] Frontend component added

## Testing

### 1. Check Flask Service Health

```bash
curl http://localhost:5000/api/v1/detect/health
```

### 2. Test AI Detection Endpoint

```bash
curl -X POST http://localhost:8080/api/v1/submissions/1/analyze-ai
```

### 3. Verify Supabase Record

Check Supabase `plagiarism_detections` table for results.

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|---|---|---|
| Connection refused | Flask not running | Start Flask service |
| 401 Unauthorized | Invalid HF token | Check `.env` file |
| Timeout | Large file | Reduce file size |
| Null response | Supabase down | Check Supabase status |

---

**Done!** Your Spring Boot backend is now connected to the AI detection service.
