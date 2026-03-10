# Phase 7 - Advanced Profile, Resume & Intelligence System

## 🚀 Deployment Guide

### Environment Setup

1. **Install Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Environment Variables**
Copy `.env.example` to `.env` and configure:

```bash
# Required for production
SECRET_KEY=your-random-secret-key-here
DATABASE_URL=your-production-database-url

# Email Configuration (Required for verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_FROM=your-email@gmail.com

# Cloud Storage (Optional - defaults to local)
USE_CLOUD_STORAGE=true
STORAGE_TYPE=s3  # or cloudinary
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
```

### Database Setup

The database tables will be created automatically on first run. New tables added in Phase 7:

- `email_verification_tokens` - Email verification tokens
- `profile_views` - Profile view tracking
- `notifications` - User notifications
- `job_applications` - Job application tracking

### Render Deployment

1. **Update `render.yaml`**
```yaml
services:
  - type: web
    name: placement-portal-backend
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app.main:app"
    envVars:
      - key: PYTHON_VERSION
        value: "3.9"
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        fromDatabase:
          name: placement-db
          property: connectionString
      - key: SMTP_HOST
        value: "smtp.gmail.com"
      - key: SMTP_PORT
        value: "587"
      - key: SMTP_USER
        sync: false
      - key: SMTP_PASS
        sync: false
      - key: EMAIL_FROM
        sync: false
      - key: USE_CLOUD_STORAGE
        value: "false"  # Set to true for production with cloud storage

databases:
  - name: placement-db
    databaseName: placement
    user: placement_user
```

2. **Deploy to Render**
```bash
git add .
git commit -m "Phase 7: Advanced Profile, Resume & Intelligence System"
git push origin main
```

## 🧪 Testing Guide

### 1. Email Verification Testing

**Test Email Setup:**
```bash
# Test SMTP configuration
python -c "
from app.utils.email import send_email
send_email('test@example.com', 'Test', '<h1>Test Email</h1>')
"
```

**Test Registration Flow:**
1. Register new user (any role)
2. Check email for verification link
3. Click verification link
4. Try login before and after verification

**API Endpoints:**
```bash
# Register user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "role": "student"}'

# Resend verification
curl -X POST "http://localhost:8000/auth/resend-verification?email=test@example.com&role=student"

# Verify email
curl "http://localhost:8000/auth/verify-email?token=YOUR_TOKEN_HERE"
```

### 2. Cloud Storage Testing

**Test Local Storage:**
```bash
# Upload resume
curl -X POST "http://localhost:8000/student/upload-resume" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_resume.pdf"
```

**Test Cloud Storage (AWS S3):**
1. Configure AWS credentials in `.env`
2. Set `USE_CLOUD_STORAGE=true` and `STORAGE_TYPE=s3`
3. Test upload - should return S3 URL

**Test Cloudinary:**
1. Configure Cloudinary credentials
2. Set `STORAGE_TYPE=cloudinary`
3. Test upload - should return Cloudinary URL

### 3. Profile Views Testing

**Test Profile View Tracking:**
```bash
# Admin views student profile
curl -X POST "http://localhost:8000/admin/profile/view/1" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Company views student profile
curl -X POST "http://localhost:8000/company/profile/view/1" \
  -H "Authorization: Bearer COMPANY_TOKEN"

# Get profile views
curl "http://localhost:8000/student/profile-views" \
  -H "Authorization: Bearer STUDENT_TOKEN"
```

### 4. ATS Resume Analysis Testing

**Test Resume Analysis:**
```bash
# Analyze resume
curl -X POST "http://localhost:8000/resume/analyze" \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -F "file=@resume.pdf"

# Score resume for specific job
curl -X POST "http://localhost:8000/resume/score/1" \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -F "file=@resume.pdf"
```

### 5. Notifications Testing

**Test Notification System:**
```bash
# Get notifications
curl "http://localhost:8000/student/notifications" \
  -H "Authorization: Bearer STUDENT_TOKEN"

# Mark notification as read
curl -X POST "http://localhost:8000/student/notifications/1/read" \
  -H "Authorization: Bearer STUDENT_TOKEN"

# Mark all as read
curl -X POST "http://localhost:8000/student/notifications/mark-all-read" \
  -H "Authorization: Bearer STUDENT_TOKEN"
```

### 6. Security Testing

**Test Rate Limiting:**
```bash
# Make many requests to test rate limiting
for i in {1..1001}; do
  curl "http://localhost:8000/" &
done
# Should return 429 after 1000 requests
```

**Test Login Security:**
```bash
# Try multiple failed logins
for i in {1..6}; do
  curl -X POST "http://localhost:8000/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=wrongpassword"
done
# Should lock account after 5 attempts
```

## 🔧 Frontend Integration

### Update Frontend API Calls

Add these new endpoints to `frontend/js/api.js`:

```javascript
// Resume Analysis
aiResumeReview: () => authFetch("/student/ai-resume-review", { method: "POST" }),
analyzeResume: (file) => {
  const token = localStorage.getItem("auth_token");
  const form = new FormData();
  form.append("file", file);
  return fetch(`${API_BASE}/resume/analyze`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  }).then(handleResponse);
},

// Profile Views
getProfileViews: () => authFetch("/student/profile-views"),
logProfileView: (studentId) => authFetch(`/admin/profile/view/${studentId}`, { method: "POST" }),

// Enhanced Notifications
getNotifications: () => authFetch("/student/notifications"),
markNotificationRead: (id) => authFetch(`/student/notifications/${id}/read`, { method: "POST" }),
markAllNotificationsRead: () => authFetch("/student/notifications/mark-all-read", { method: "POST" }),
```

### New Frontend Features

1. **Email Verification UI**
   - Show verification message on signup
   - Add resend verification button
   - Handle verified/unverified states

2. **ATS Resume Analysis**
   - Resume upload with progress indicator
   - ATS score visualization
   - Missing keywords display
   - Improvement suggestions

3. **Profile Views Dashboard**
   - "Who viewed my profile" section
   - View statistics and analytics
   - Company/admin viewer identification

4. **Enhanced Notifications**
   - Real-time notification bell
   - Notification dropdown
   - Mark as read functionality
   - Email notification preferences

## 📊 Monitoring & Analytics

### Admin Analytics

Access profile view analytics:
```bash
curl "http://localhost:8000/admin/profile-views-analytics" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Key Metrics to Track

1. **Profile Engagement**
   - Most viewed students
   - Profile view frequency
   - Viewer demographics (admin/company/student)

2. **Resume Performance**
   - ATS score distribution
   - Common missing keywords
   - Upload success rates

3. **Email Verification**
   - Verification completion rate
   - Email delivery success
   - Token expiration rates

## 🚨 Troubleshooting

### Common Issues

1. **Email Not Sending**
   - Check SMTP credentials
   - Verify app passwords for Gmail
   - Check firewall/port settings

2. **Cloud Storage Upload Failing**
   - Verify AWS/Cloudinary credentials
   - Check bucket permissions
   - Ensure file size limits

3. **Rate Limiting Too Strict**
   - Adjust `RATE_LIMIT_REQUESTS` in `.env`
   - Check for stuck rate limit entries
   - Monitor API usage patterns

4. **PDF Parsing Errors**
   - Ensure valid PDF format
   - Check file size limits
   - Verify PyPDF2 installation

### Debug Mode

Enable debug logging:
```bash
export PYTHONPATH=.
python -c "
from app.utils.email import send_email
from app.utils.storage import storage_manager
print('Email config:', bool(os.getenv('SMTP_HOST')))
print('Storage type:', storage_manager.storage_type)
"
```

## 🎯 Performance Optimization

1. **Database Indexes**
   - Add indexes for frequently queried fields
   - Monitor query performance
   - Optimize slow queries

2. **File Storage**
   - Use CDN for resume files
   - Implement file caching
   - Monitor storage costs

3. **Rate Limiting**
   - Use Redis for distributed rate limiting
   - Implement different limits per endpoint
   - Monitor rate limit hit rates

## 🔐 Security Checklist

- [ ] JWT secrets are randomized
- [ ] SMTP credentials are secure
- [ ] Cloud storage permissions are minimal
- [ ] Rate limiting is enabled
- [ ] File uploads are validated
- [ ] Security headers are present
- [ ] Login attempt tracking is enabled
- [ ] Email verification tokens expire

## 📈 Production Readiness

1. **Load Testing**
   - Test with concurrent users
   - Verify rate limiting performance
   - Monitor memory usage

2. **Backup Strategy**
   - Database backups
   - File storage backups
   - Configuration backups

3. **Monitoring**
   - Error tracking
   - Performance metrics
   - User activity logs

4. **Scaling**
   - Horizontal scaling readiness
   - Database connection pooling
   - CDN integration
