# 🧠 Wolfstitch Cloud - AI Dataset Preparation Platform

**Transform any document into AI-ready training data in seconds.**

[![Production Status](https://img.shields.io/badge/Status-Live%20Production-brightgreen)](https://wolfstitch.dev)
[![API Health](https://img.shields.io/badge/API-Operational-success)](https://api.wolfstitch.dev/health)
[![Railway Deployment](https://img.shields.io/badge/Deployed%20on-Railway-blueviolet)](https://railway.app)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

---

## 🌟 **Live Platform**

**🔗 [wolfstitch.dev](https://wolfstitch.dev)** - Start processing files immediately  
**📡 [API Documentation](https://api.wolfstitch.dev/docs)** - Complete API reference  
**❤️ [Health Status](https://api.wolfstitch.dev/health)** - System monitoring

---

## ✨ **What is Wolfstitch Cloud?**

Wolfstitch Cloud is a powerful, production-ready platform that transforms documents into AI-training datasets. Upload any file, get back perfectly chunked, tokenized data ready for machine learning pipelines.

### **🎯 Perfect For:**
- **AI/ML Engineers** preparing training datasets
- **Data Scientists** processing research documents
- **Developers** building AI applications
- **Businesses** creating custom AI models

---

## 🚀 **Key Features**

### **📄 Universal Document Support**
- **40+ File Formats**: PDF, DOCX, TXT, XLSX, CSV, HTML, MD, EPUB, and more
- **Smart Text Extraction**: Advanced parsing preserves document structure
- **Content Preservation**: Maintains formatting and context

### **🧠 Intelligent Chunking**
- **Semantic Boundaries**: Splits at logical content breaks
- **Configurable Size**: Optimized for AI model context windows
- **Token Accuracy**: Precise GPT-4 compatible token counting
- **Metadata Rich**: Timestamps, filenames, and processing details

### **⚡ Production Performance**
- **Lightning Fast**: Process 1MB files in under 10 seconds
- **Scalable**: Cloud-native architecture handles any volume
- **99.9% Uptime**: Enterprise-grade reliability
- **Global CDN**: Fast access worldwide

### **🔒 Enterprise Security**
- **HTTPS Everywhere**: End-to-end encryption
- **No Data Storage**: Files processed and discarded immediately
- **Privacy First**: Your data never leaves the processing pipeline
- **Compliance Ready**: SOC 2 compatible infrastructure

---

## 📊 **Live Demo Results**

### **Input Document Types Tested:**
```
✅ Academic Research Papers     → 1-2 chunks, 800+ tokens each
✅ Business Strategy Documents  → 2-3 chunks, 500-600 tokens each  
✅ Legal Agreements            → 2-4 chunks, 700-900 tokens each
✅ Technical Documentation     → Variable chunks, optimized sizing
✅ Financial Reports           → Table-aware chunking
```

### **Output Quality:**
```json
{
  "text": "# Advanced Neural Network Architectures...",
  "chunk_id": 1,
  "tokens": 820,
  "metadata": {
    "filename": "research_paper.pdf",
    "processed_at": "2025-06-20T21:58:36.198Z"
  }
}
```

---

## 🛠️ **How to Use**

### **🌐 Web Interface**
1. **Visit [wolfstitch.dev](https://wolfstitch.dev)**
2. **Upload your document** (drag & drop or click)
3. **Wait for processing** (usually < 30 seconds)
4. **Download JSONL results** (ready for AI training)

### **🔌 API Integration**
```bash
curl -X POST "https://api.wolfstitch.dev/api/v1/quick-process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf" \
  -F "tokenizer=gpt-4" \
  -F "max_tokens=1000"
```

### **📦 Response Format**
```json
{
  "message": "File processed successfully",
  "filename": "your-document.pdf",
  "chunks": 3,
  "total_tokens": 2019,
  "average_chunk_size": 673,
  "preview": [
    {
      "text": "Document content preview...",
      "tokens": 820
    }
  ]
}
```

---

## 🏗️ **Architecture**

### **Frontend (Next.js 15)**
- **Modern React** with TypeScript
- **Tailwind CSS** design system
- **Mobile-first** responsive design
- **Real-time processing** status

### **Backend (FastAPI + Python)**
- **Wolfcore Library** for document processing
- **Railway Cloud** deployment
- **PostgreSQL + Redis** for scaling
- **Graceful error handling** and logging

### **Infrastructure**
- **Cloudflare CDN** for global performance
- **Custom domain** with SSL certificates
- **Auto-scaling** based on demand
- **Health monitoring** and alerting

---

## 📈 **Performance Metrics**

| Metric | Value |
|--------|-------|
| **Processing Speed** | < 10 seconds for 1MB files |
| **Supported Formats** | 40+ document types |
| **API Uptime** | 99.9%+ |
| **Max File Size** | 100MB |
| **Token Accuracy** | GPT-4 compatible |
| **Global Latency** | < 200ms (CDN optimized) |

---

## 🔧 **Development**

### **Prerequisites**
- Node.js 18+
- Python 3.9+
- Git

### **Local Setup**
```bash
# Clone repository
git clone https://github.com/CLewisMessina/wolfstitch-cloud-dev.git
cd wolfstitch-cloud-dev

# Frontend development
cd frontend
npm install
npm run dev  # → http://localhost:3000

# Backend development (optional - API is live)
pip install -r requirements.txt
uvicorn backend.main:app --reload  # → http://localhost:8000
```

### **Environment Variables**
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://api.wolfstitch.dev
NEXT_PUBLIC_ENVIRONMENT=production

# Backend (Railway managed)
ENVIRONMENT=production
DATABASE_URL=[auto-configured]
REDIS_URL=[auto-configured]
```

---

## 🧪 **Testing**

### **Automated Testing**
```bash
# Run validation script
python setup_railway.py

# Frontend tests
cd frontend && npm test

# Backend tests
pytest backend/tests/
```

### **Manual Testing**
1. Upload test documents from `/test-files/`
2. Verify chunking quality and token accuracy
3. Test download functionality
4. Check error handling with invalid files

---

## 🚀 **Deployment**

### **Production Stack**
- **Frontend**: Railway (gentle-unity service)
- **Backend**: Railway (wolfstitch-cloud-dev service)
- **Database**: Railway PostgreSQL
- **Cache**: Railway Redis
- **DNS**: Cloudflare
- **Domain**: GoDaddy registration

### **Continuous Deployment**
- **GitHub Integration**: Auto-deploy on push to main
- **Build Validation**: Automated testing pipeline
- **Health Checks**: Monitoring and alerting
- **Rollback**: Instant revert capability

---

## 📊 **Monitoring & Analytics**

### **Health Endpoints**
- **API Health**: [/health](https://api.wolfstitch.dev/health)
- **System Status**: Real-time metrics
- **Performance Monitoring**: Response times and throughput

### **Usage Analytics**
- Processing volume and success rates
- File type distribution
- Performance benchmarks
- Error tracking and resolution

---

## 🤝 **Contributing**

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### **Development Workflow**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🎯 **Roadmap**

### **Coming Soon**
- **Batch Processing**: Upload multiple files simultaneously
- **Custom Chunking**: User-defined chunk size and overlap
- **Export Formats**: CSV, TXT, and custom formats
- **API Authentication**: Secure access with API keys

### **Future Features**
- **Team Collaboration**: Shared workspaces and projects
- **Advanced Analytics**: Detailed processing insights
- **Webhook Integration**: Real-time processing notifications
- **Enterprise SSO**: Advanced authentication options

---

## 📞 **Support**

### **Need Help?**
- **📖 Documentation**: [API Docs](https://api.wolfstitch.dev/docs)
- **💬 Issues**: [GitHub Issues](https://github.com/CLewisMessina/wolfstitch-cloud-dev/issues)
- **📧 Contact**: [clewis@wolfstitch.dev](mailto:clewis@wolfstitch.dev)
- **💼 LinkedIn**: [@CLewisMessina](https://linkedin.com/in/clewismessina)

### **Status & Updates**
- **🔔 System Status**: [status.wolfstitch.dev](https://status.wolfstitch.dev)
- **📰 Product Updates**: Follow on LinkedIn for announcements

---

## 🏆 **Built With Excellence**

**Wolfstitch Cloud** represents the culmination of modern web development practices, enterprise-grade infrastructure, and user-centered design. From initial concept to production deployment, every aspect has been crafted for performance, reliability, and developer experience.

### **Technology Stack**
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python, Wolfcore Library
- **Infrastructure**: Railway, Cloudflare, PostgreSQL, Redis
- **Development**: Git, GitHub, VS Code, Modern DevOps

---

**Ready to transform your documents into AI training data?**

## **🚀 [Start Processing Files Now →](https://wolfstitch.dev)**

---

*Made with ❤️ by [Chris Lewis-Messina](https://linkedin.com/in/clewismessina)*