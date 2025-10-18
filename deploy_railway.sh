#!/bin/bash

# Railway Deployment Script for Intercom Analysis Tool
# This script helps deploy the chat interface to Railway

echo "🚀 Railway Deployment Helper"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found. Please run this from the project root."
    exit 1
fi

echo "✅ Found Dockerfile and deployment files"

# Check if Railway CLI is available
if command -v railway &> /dev/null; then
    echo "✅ Railway CLI found"
    RAILWAY_CMD="railway"
elif command -v npx &> /dev/null; then
    echo "✅ Using npx for Railway CLI"
    RAILWAY_CMD="npx @railway/cli"
else
    echo "❌ Neither railway CLI nor npx found"
    echo "Please install Node.js and try again"
    exit 1
fi

echo ""
echo "📋 Deployment Steps:"
echo "1. Go to https://railway.app/dashboard"
echo "2. Click 'New Project'"
echo "3. Select 'Deploy from GitHub repo'"
echo "4. Search for: maxjackson-lab/intercom-gamma-analyzer"
echo "5. Select the repository"
echo "6. Railway will automatically detect the Dockerfile"
echo ""

echo "🔧 Environment Variables to Set in Railway:"
echo "INTERCOM_ACCESS_TOKEN=your_intercom_token"
echo "OPENAI_API_KEY=your_openai_key"
echo "GAMMA_API_KEY=your_gamma_key"
echo "INTERCOM_WORKSPACE_ID=your_workspace_id"
echo "DEPLOYMENT_MODE=web"
echo "WEB_PASSWORD=your_secure_password"
echo ""

echo "🌐 After deployment, your app will be available at:"
echo "https://your-app-name.railway.app"
echo ""

echo "🧪 Test endpoints:"
echo "- Health: https://your-app-name.railway.app/health"
echo "- Chat UI: https://your-app-name.railway.app/"
echo "- API: https://your-app-name.railway.app/api/commands"
echo ""

echo "📊 Expected features:"
echo "✅ Natural language chat interface"
echo "✅ Command translation (voice-of-customer, billing-analysis, etc.)"
echo "✅ Gamma presentation URL generation"
echo "✅ Custom filter building"
echo "✅ Security framework with input validation"
echo "✅ Performance monitoring"
echo ""

echo "🎉 Ready for deployment!"
echo "If you encounter issues with GitHub connection, try:"
echo "1. Re-authorize Railway in GitHub settings"
echo "2. Check repository visibility"
echo "3. Use 'Empty Project' and upload files manually"

