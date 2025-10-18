# Railway GitHub Connection Troubleshooting

## 🚨 Common Issues & Solutions

### **Issue: Railway Can't Find Your Repository**

**Symptoms:**
- Repository doesn't appear in search
- "Repository not found" error
- Connection fails during setup

**Solutions:**

#### **1. Check Repository Visibility**
```bash
# Verify your repository exists and is accessible
curl -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/maxjackson-lab/intercom-gamma-analyzer
```

#### **2. Re-authorize Railway in GitHub**
1. Go to [GitHub Settings → Applications → Authorized OAuth Apps](https://github.com/settings/applications)
2. Find "Railway" in the list
3. Click "Revoke access"
4. Go back to Railway and reconnect GitHub
5. Grant all necessary permissions

#### **3. Check GitHub Organization Permissions**
- If `maxjackson-lab` is an organization, make sure Railway has access
- Go to Organization Settings → Third-party access
- Ensure Railway is authorized

#### **4. Try Different Repository Name Formats**
- `maxjackson-lab/intercom-gamma-analyzer`
- `intercom-gamma-analyzer`
- `maxjackson-lab/intercom-gamma-analyzer.git`

### **Issue: Permission Denied**

**Solutions:**

#### **1. Check Repository Access**
- Make sure your GitHub account has access to the repository
- If it's an organization repo, ensure you're a member

#### **2. Verify Railway Permissions**
- Railway needs: `repo`, `read:org`, `user:email` permissions
- Re-authorize if permissions are insufficient

### **Issue: Repository Shows as Private**

**Solutions:**

#### **1. Make Repository Public (Temporary)**
```bash
# Go to repository settings on GitHub
# Change visibility to "Public"
# Deploy on Railway
# Change back to "Private" if needed
```

#### **2. Grant Railway Access to Private Repos**
- In Railway settings, ensure "Private repositories" is enabled
- Re-authorize GitHub connection

## 🔧 Alternative Deployment Methods

### **Method 1: Manual File Upload**

1. **Create Empty Project**
   - Go to Railway dashboard
   - Click "New Project" → "Empty Project"

2. **Upload Files**
   - Railway provides a deployment URL
   - Use git push or file upload

3. **Set Environment Variables**
   - Add all required API keys in Railway dashboard

### **Method 2: Railway CLI (Local)**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login (requires interactive terminal)
railway login

# Initialize project
railway init

# Deploy
railway up
```

### **Method 3: GitHub Actions**

Create `.github/workflows/railway-deploy.yml`:

```yaml
name: Deploy to Railway
on:
  push:
    branches: [main, feature/comprehensive-code-review]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: railway-app/railway-deploy@v1
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
```

## 🎯 Quick Fix Checklist

- [ ] Repository is accessible: `https://github.com/maxjackson-lab/intercom-gamma-analyzer`
- [ ] GitHub account has access to the repository
- [ ] Railway is authorized in GitHub settings
- [ ] Railway has permission for private repositories (if applicable)
- [ ] Repository name is spelled correctly
- [ ] Try re-authorizing Railway in GitHub settings
- [ ] Check organization permissions (if applicable)

## 🚀 Manual Deployment Steps

If all else fails, use manual deployment:

1. **Create Railway Project**
   - Go to [railway.app/dashboard](https://railway.app/dashboard)
   - Click "New Project" → "Empty Project"

2. **Configure Build Settings**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python deploy/railway_web.py`
   - Health Check Path: `/health`

3. **Set Environment Variables**
   ```
   INTERCOM_ACCESS_TOKEN=your_token
   OPENAI_API_KEY=your_key
   GAMMA_API_KEY=your_key
   INTERCOM_WORKSPACE_ID=your_id
   DEPLOYMENT_MODE=web
   WEB_PASSWORD=your_password
   ```

4. **Deploy**
   - Railway will build and deploy automatically
   - Get your URL from the dashboard

## 📞 Support Resources

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **GitHub Issues**: Create an issue in your repository

## ✅ Success Indicators

After successful deployment:
- Health check returns: `{"status": "healthy", "chat_interface": true}`
- Web interface loads at your Railway URL
- API endpoints respond correctly
- Chat interface processes natural language queries

