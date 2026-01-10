#!/bin/bash

################################################################################
# Quick API Key Setup Script
################################################################################

echo "================================================================================"
echo "Gemini API Key Setup"
echo "================================================================================"
echo ""

# Check if API key is already set
if [ -n "$LANGEXTRACT_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
    echo "✓ API key already configured!"
    echo ""
    if [ -n "$LANGEXTRACT_API_KEY" ]; then
        echo "  LANGEXTRACT_API_KEY is set"
    fi
    if [ -n "$GOOGLE_API_KEY" ]; then
        echo "  GOOGLE_API_KEY is set"
    fi
    echo ""
    echo "You can run the test script now:"
    echo "  ./test_single_extraction.sh"
    echo ""
    exit 0
fi

# Check if .env exists
if [ -f "/app/.env" ]; then
    source /app/.env
    if [ -n "$LANGEXTRACT_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
        echo "✓ API key found in .env file!"
        echo ""
        echo "The test script will automatically load it."
        echo ""
        echo "You can run the test script now:"
        echo "  ./test_single_extraction.sh"
        echo ""
        exit 0
    fi
fi

echo "No API key found. Let's set it up!"
echo ""
echo "Choose your preferred method:"
echo ""
echo "1. Create .env file (recommended - persistent across sessions)"
echo "2. Export environment variable (current session only)"
echo "3. Show instructions only"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Get your API key from: https://aistudio.google.com/app/apikey"
        echo ""
        read -p "Enter your Gemini API key: " api_key

        if [ -z "$api_key" ]; then
            echo "Error: No API key provided"
            exit 1
        fi

        echo "LANGEXTRACT_API_KEY=$api_key" > /app/.env
        chmod 600 /app/.env  # Secure the file

        echo ""
        echo "✓ API key saved to /app/.env"
        echo ""
        echo "The test script will automatically load it."
        echo ""
        echo "You can run the test script now:"
        echo "  ./test_single_extraction.sh"
        echo ""
        ;;

    2)
        echo ""
        echo "Get your API key from: https://aistudio.google.com/app/apikey"
        echo ""
        read -p "Enter your Gemini API key: " api_key

        if [ -z "$api_key" ]; then
            echo "Error: No API key provided"
            exit 1
        fi

        export LANGEXTRACT_API_KEY="$api_key"

        echo ""
        echo "✓ API key exported to environment"
        echo ""
        echo "Note: This is only active for the current terminal session."
        echo ""
        echo "To make it permanent, add to your .bashrc:"
        echo "  echo 'export LANGEXTRACT_API_KEY=\"$api_key\"' >> ~/.bashrc"
        echo ""
        echo "You can run the test script now:"
        echo "  ./test_single_extraction.sh"
        echo ""
        ;;

    3)
        echo ""
        echo "================================================================================"
        echo "Manual Setup Instructions"
        echo "================================================================================"
        echo ""
        echo "Get your API key from: https://aistudio.google.com/app/apikey"
        echo ""
        echo "Then choose one of these methods:"
        echo ""
        echo "METHOD 1: Create .env file (recommended)"
        echo "  echo 'LANGEXTRACT_API_KEY=your-api-key-here' > /app/.env"
        echo "  chmod 600 /app/.env"
        echo ""
        echo "METHOD 2: Export environment variable (current session)"
        echo "  export LANGEXTRACT_API_KEY='your-api-key-here'"
        echo ""
        echo "METHOD 3: Add to .bashrc (permanent)"
        echo "  echo 'export LANGEXTRACT_API_KEY=\"your-api-key-here\"' >> ~/.bashrc"
        echo "  source ~/.bashrc"
        echo ""
        echo "METHOD 4: Set in test script (not recommended)"
        echo "  nano test_single_extraction.sh"
        echo "  # Uncomment and set: GEMINI_API_KEY=\"your-api-key-here\""
        echo ""
        echo "================================================================================"
        echo ""
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
