#!/bin/bash
#
# Setup script to configure local environment with OpenAI API key
# Usage: ./scripts/setup-env.sh
#

set -e

echo "🔧 Setting up local development environment..."

# Prompt user to enter the API key manually
echo "🔑 Please enter your OpenAI API key:"
echo "📋 Get your API key from: https://platform.openai.com/api-keys"
echo ""
read -p "🔑 Paste your OpenAI API key here: " OPENAI_API_KEY

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ No API key provided"
    exit 1
fi

# Validate API key format (basic check for OpenAI format)
if [[ ! "$OPENAI_API_KEY" =~ ^sk-.* ]] || [ ${#OPENAI_API_KEY} -lt 40 ]; then
    echo "❌ API key format invalid. OpenAI keys should start with 'sk-' and be ~51 characters long."
    exit 1
fi

# Update .env file with real API key
echo "📝 Updating .env file with real API key..."
if [ -f .env ]; then
    # Replace the placeholder with real key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_API_KEY/" .env
    else
        # Linux
        sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_API_KEY/" .env
    fi
    echo "✅ Updated existing .env file"
else
    echo "❌ .env file not found. Please copy from .env.example first"
    exit 1
fi

echo "🎉 Environment setup complete!"
echo "📋 You can now run tests with real API integration:"
echo "   uv run pytest tests/test_services/test_nlp_service.py::TestNLPServiceRealAPI -v"